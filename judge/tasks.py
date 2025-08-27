import docker
import tempfile
import os
import logging
import requests
from celery import shared_task
from django.apps import apps
import ast

logger = logging.getLogger(__name__)

# Add language-specific execution logic
LANGUAGE_CONFIGS = {
    'python': {
        'image': 'python:3.9-slim',
        'command': 'python /app/code.py',
        'extension': '.py'
    },
    'javascript': {
        'image': 'node:16-slim',
        'command': 'node /app/code.js',
        'extension': '.js'
    },
    # Add more languages as needed
}

def get_docker_client():
    """Get Docker client with proper error handling"""
    try:
        # Try standard connection
        client = docker.from_env()
        client.ping()  # Test connection
        return client
    except docker.errors.DockerException as e:
        logger.error(f"Docker connection failed: {e}")
        # Try Windows-specific connection
        try:
            client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
            client.ping()
            return client
        except docker.errors.DockerException as e2:
            logger.error(f"Windows Docker connection also failed: {e2}")
            return None

@shared_task(bind=True, max_retries=3)
def judge_submission(self, submission_id):
    code_file = None
    try:
        Submission = apps.get_model('submissions', 'Submission')
        TestCase = apps.get_model('problems', 'TestCase')
        
        submission = Submission.objects.get(id=submission_id)
        problem = submission.problem
        test_cases = TestCase.objects.filter(problem=problem)
        language = submission.language
        
        # Update submission status
        submission.verdict = 'Judging'
        submission.save()
        
        # Get language configuration
        config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS['python'])
        
        # Create a temporary file with the user's code
        with tempfile.NamedTemporaryFile(mode='w', suffix=config['extension'], delete=False) as f:
            f.write(submission.code)
            code_file = f.name
            logger.info(f"Temporary code file created: {code_file}")

        # Get Docker client
        client = get_docker_client()
        if client is None:
            logger.error("Docker is not available, using fallback execution")
            return self.retry(countdown=30)  # Retry after 30 seconds
        
        passed_tests = 0
        total_tests = test_cases.count()
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"Running test case {i+1}/{total_tests}")
            
            # Create a temporary input file
            input_file_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as input_file:
                    # Replace literal '\n' with actual newlines
                    formatted_input = test_case.input.replace('\\n', '\n')
                    input_file.write(formatted_input)
                    input_file_path = input_file.name
                
                # Run the code in a container with input from file
                container_output = client.containers.run(
                    config['image'],
                    f'sh -c "cat /app/input.txt | {config["command"]}"',
                    volumes={
                        code_file: {'bind': f'/app/code{config["extension"]}', 'mode': 'ro'},
                        input_file_path: {'bind': '/app/input.txt', 'mode': 'ro'}
                    },
                    working_dir='/app',
                    remove=True,
                    mem_limit='100m',
                )
                
                output = container_output.decode('utf-8').strip()
                expected = test_case.expected_output.strip()
                logger.info(f"Expected: {expected} | Got: {output}")

                try:
                    parsed_output = ast.literal_eval(output)
                    parsed_expected = ast.literal_eval(expected)
                except Exception as e:
                    logger.error(f"Failed to parse output/expected: {e}")
                    submission.verdict = 'RE'
                    submission.save()
                    break


                # Check if the output matches the expected output
                if parsed_output == parsed_expected:
                    passed_tests += 1
                else:
                    submission.verdict = 'WA'  # Wrong Answer
                    submission.save()
                    break
                    
            except docker.errors.ContainerError as e:
                # Container exited with a non-zero status
                logger.error(f"Container error: {e}")
                submission.verdict = 'RE'  # Runtime Error
                submission.save()
                break
                
            except requests.exceptions.ReadTimeout:
                logger.error("Container timeout")
                submission.verdict = 'TLE'  # Time Limit Exceeded
                submission.save()
                break
                
            except Exception as e:
                logger.error(f"Error executing test case: {e}")
                submission.verdict = 'RE'  # Runtime Error
                submission.save()
                break
                
            finally:
                # Clean up input file
                try:
                    if input_file_path and os.path.exists(input_file_path):
                        os.remove(input_file_path)
                except:
                    pass  # Ignore cleanup errors
                
        else:
            # All test cases passed
            submission.verdict = 'AC'  # Accepted
            submission.execution_time = 0.5  # Simulated time
            submission.memory_used = 10.5   # Simulated memory
            submission.save()
            logger.info(f"Submission {submission_id} judged successfully")
            
    except Exception as e:
        logger.error(f"Error in judge_submission task: {e}")
        # Update submission status to indicate error
        try:
            submission.verdict = 'RE'
            submission.save()
        except:
            pass  # If we can't save, at least log the error
        
        # Retry the task
        try:
            self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for submission {submission_id}")
            
    finally:
        # Clean up temporary file
        try:
            if code_file and os.path.exists(code_file):
                os.remove(code_file)
        except:
            pass  # Ignore cleanup errors

@shared_task
def analyze_submission(submission_id):
    try:
        Submission = apps.get_model('submissions', 'Submission')
        submission = Submission.objects.get(id=submission_id)
        
        # Update AI status
        submission.ai_status = 'Processing'
        submission.save()
        
        # Simulate AI analysis
        import time
        time.sleep(2)
        
        # Generate simulated feedback
        submission.ai_feedback = f"""
        AI Analysis for Submission #{submission_id}:
        
        Code Quality: Good
        Efficiency: Could be improved
        Readability: Excellent
        
        Suggestions:
        1. Consider using more efficient data structures
        2. Add comments for complex logic
        3. Handle edge cases more gracefully
        """
        submission.ai_status = 'Completed'
        submission.save()
        
    except Exception as e:
        logger.error(f"Error in analyze_submission task: {e}")
        try:
            submission.ai_status = 'Failed'
            submission.save()
        except:
            pass