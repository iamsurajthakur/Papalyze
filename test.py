from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Replace with your actual credentials
DATABASE_URI = "postgresql://mmamc:urus@localhost/mmamc"

def test_connection():
    print(f"Connecting to: {DATABASE_URI}")
    engine = create_engine(DATABASE_URI)

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            print("Connection successful!")
            for row in result:
                print(f"PostgreSQL version: {row[0]}")
    except OperationalError as e:
        print("Connection failed.")
        print(str(e))

if __name__ == "__main__":
    test_connection()
