"""
Run script for the ERP application
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
