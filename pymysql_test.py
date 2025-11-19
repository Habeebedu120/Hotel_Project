# test_conn.py
import pymysql
try:
    conn = pymysql.connect(host='127.0.0.1', user='root', password='YourPassword', port=3306, database='mysql')
    print("Connected")
    conn.close()
except Exception as e:
    print("Error:", type(e).__name__, e)
