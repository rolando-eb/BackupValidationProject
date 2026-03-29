# run_local.py
from sandbox_backup_sqlraw_to_rds import lambda_handler

if __name__ == "__main__":
    # Simulate an empty test event
    result = lambda_handler(event={}, context=None)
    print(result)