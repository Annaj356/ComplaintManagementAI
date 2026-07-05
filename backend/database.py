<<<<<<< HEAD
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="complaint_management_ai"
=======
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="complaint_system"
>>>>>>> 45d8bc0121f9aff758b3155930da15098b4028af
    )