from .database import engine, Base
from .models import User, CoverLetterHistory, InterviewReport

def recreate_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database has been recreated successfully.")

if __name__ == "__main__":
    recreate_db()
