import docker
import tempfile
import os
import logging
import platform
import time
import subprocess
from celery import shared_task
from django.apps import apps
import ast

logger = logging.getLogger(__name__)

# Add language-specific execution logic
LANGUAGE_CONFIGS = {
    'python': {
        'image': 'python:3.9-slim',
        'command': 'python',
        'extension': '.py',
        'local_command': 'python'
    },
    'javascript': {
        'image': 'node:16-slim',
        'command': 'node',
        'extension': '.js',
        'local_command': 'node'
    },
    # Add more languages as needed
}

def get_docker_client():
    """Get Docker client with proper handling for Windows"""
    try:
        # Try different connection methods
        connection_methods = [
            'npipe:////./pipe/docker_engine',  # Windows named pipe
            'tcp://localhost:2375',            # Docker daemon TCP
            'unix://var/run/docker.sock',      # Linux socket
        ]
        
        client = None
        for base_url in connection_methods:
            try:
                logger.info(f"Trying Docker connection: {base_url}")
                client = docker.DockerClient(base_url=base_url, timeout=30)
                client.ping()  # Test connection
                logger.info(f"Successfully connected to Docker via {base_url}")
                return client
            except Exception as e:
                logger.warning(f"Failed to connect via {base_url}: {e}")
                continue
        
        # If all methods fail, try default environment
        try:
            client = docker.from_env(timeout=30)
            client.ping()
            logger.info("Successfully connected to Docker via default environment")
            return client
        except Exception as e:
            logger.error(f"All Docker connection methods failed: {e}")
            return None
            
    except docker.errors.DockerException as e:
        logger.error(f"Docker connection failed: {e}")
        return None

def execute_code_locally(code_file, input_data, language, timeout=5):
    """Fallback execution without Docker"""
    try:
        config = LANGUAGE_CONFIGS.get(language, LANGUAGE_CONFIGS['python'])
        
        # Prepare command
        if language == 'python':
            cmd = [config['local_command'], code_file]
        elif language == 'javascript':
            cmd = [config['local_command'], code_file]
        else:
            cmd = [config['local_command'], code_file]
        
        # Execute with input - FIXED: removed timeout from Popen
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Replace literal '\n' with actual newlines in input
        formatted_input = input_data.replace('\\n', '\n')
        
        try:
            stdout, stderr = process.communicate(input=formatted_input, timeout=timeout)
            
            if process.returncode != 0:
                return None, stderr.strip()
            
            return stdout.strip(), None
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return None, "Time Limit Exceeded"
        
    except Exception as e:
        return None, str(e)

@shared_task(bind=True, max_retries=3)
def judge_submission(self, submission_id):
    code_file = None
    input_file_path = None
    
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
        with tempfile.NamedTemporaryFile(mode='w', suffix=config['extension'], delete=False, encoding='utf-8') as f:
            f.write(submission.code)
            code_file = f.name
            logger.info(f"Temporary code file created: {code_file}")

        # Try Docker first, then fallback to local execution
        client = get_docker_client()
        use_docker = client is not None
        
        passed_tests = 0
        total_tests = test_cases.count()
        execution_time = 0
        
        for i, test_case in enumerate(test_cases):
            logger.info(f"Running test case {i+1}/{total_tests}")
            
            try:
                start_time = time.time()
                output = None
                error = None
                
                if use_docker:
                    # Docker execution
                    try:
                        # Create a temporary input file
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as input_file:
                            formatted_input = test_case.input.replace('\\n', '\n')
                            input_file.write(formatted_input)
                            input_file_path = input_file.name
                        
                        # Run the code in a container with input from file
                        container = client.containers.run(
                            config['image'],
                            f'sh -c "cat /app/input.txt | {config["command"]} /app/code{config["extension"]}"',
                            volumes={
                                code_file: {'bind': f'/app/code{config["extension"]}', 'mode': 'ro'},
                                input_file_path: {'bind': '/app/input.txt', 'mode': 'ro'}
                            },
                            working_dir='/app',
                            remove=True,
                            mem_limit='100m',
                            stdout=True,
                            stderr=True,
                            detach=False
                        )
                        
                        output = container.decode('utf-8').strip()
                        
                    except docker.errors.ContainerError as e:
                        error = f"Container error: {e.stderr.decode('utf-8') if hasattr(e, 'stderr') else str(e)}"
                    except Exception as e:
                        error = f"Docker execution error: {str(e)}"
                        
                else:
                    # Local execution fallback
                    logger.info("Using local execution fallback")
                    output, error = execute_code_locally(
                        code_file, 
                        test_case.input, 
                        language
                    )
                
                execution_time = time.time() - start_time
                
                if error:
                    logger.error(f"Execution error: {error}")
                    if "Time Limit Exceeded" in error:
                        submission.verdict = 'TLE'
                    else:
                        submission.verdict = 'RE'  # Runtime Error
                    submission.save()
                    break
                
                expected = test_case.expected_output.strip()
                logger.info(f"Expected: '{expected}' | Got: '{output}'")

                # Try to parse outputs for comparison
                try:
                    # For numeric or boolean outputs
                    parsed_output = ast.literal_eval(output)
                    parsed_expected = ast.literal_eval(expected)
                    is_correct = parsed_output == parsed_expected
                    logger.info(f"Parsed comparison: {parsed_output} == {parsed_expected} -> {is_correct}")
                except:
                    # For string outputs, compare directly
                    is_correct = output == expected
                    logger.info(f"String comparison: '{output}' == '{expected}' -> {is_correct}")
                
                # Check if the output matches the expected output
                if is_correct:
                    passed_tests += 1
                    logger.info(f"Test case {i+1} passed")
                else:
                    submission.verdict = 'WA'  # Wrong Answer
                    submission.save()
                    logger.info(f"Test case {i+1} failed")
                    break
                    
            except Exception as e:
                logger.error(f"Error executing test case {i+1}: {e}")
                submission.verdict = 'RE'  # Runtime Error
                submission.save()
                break
                
            finally:
                # Clean up input file
                try:
                    if input_file_path and os.path.exists(input_file_path):
                        os.remove(input_file_path)
                        input_file_path = None
                except Exception as e:
                    logger.warning(f"Failed to clean up input file: {e}")
                
        else:
            # All test cases passed (no break)
            if passed_tests == total_tests:
                submission.verdict = 'AC'  # Accepted
                submission.execution_time = execution_time
                submission.save()
                logger.info(f"Submission {submission_id} judged successfully - All {passed_tests}/{total_tests} tests passed")
            else:
                submission.verdict = 'WA'
                submission.save()
                
    except Submission.DoesNotExist:
        logger.error(f"Submission {submission_id} does not exist")
        return
    except Exception as e:
        logger.error(f"Error in judge_submission task: {e}")
        # Update submission status to indicate error
        try:
            Submission = apps.get_model('submissions', 'Submission')
            submission = Submission.objects.get(id=submission_id)
            submission.verdict = 'RE'
            submission.save()
        except Exception as save_error:
            logger.error(f"Failed to update submission status: {save_error}")
        
        # Retry the task only for certain errors
        if "connection" in str(e).lower() or "docker" in str(e).lower():
            try:
                self.retry(exc=e, countdown=60)
            except self.MaxRetriesExceededError:
                logger.error(f"Max retries exceeded for submission {submission_id}")
        else:
            logger.error(f"Non-retryable error for submission {submission_id}")
            
    finally:
        # Clean up temporary files
        try:
            if code_file and os.path.exists(code_file):
                os.remove(code_file)
        except Exception as e:
            logger.warning(f"Failed to clean up code file: {e}")
        
        try:
            if input_file_path and os.path.exists(input_file_path):
                os.remove(input_file_path)
        except Exception as e:
            logger.warning(f"Failed to clean up input file: {e}")

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