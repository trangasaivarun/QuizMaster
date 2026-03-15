# QuizMaster

QuizMaster is a dynamic and interactive quiz web application built with Python, Flask, and SQLite. It allows users to take quizzes, tracks scores, and provides an engaging platform for testing knowledge. The application features user authentication, a timer for quizzes, leaderboards, and an admin dashboard for managing quiz content and viewing analytics.

## Technologies Used
- **Backend:** Python, Flask
- **Database:** SQLite
- **Frontend:** HTML5, CSS3, JavaScript
- **Additional:** Werkzeug for secure forms

## Features
- User registration and login
- Interactive quizzes with a timer
- Real-time score calculation and leaderboard
- Admin dashboard for adding, editing, and deleting questions
- Admin analytics and quiz review mode
- Modern, responsive, and visually appealing UI

## Setup Instructions

### Prerequisites
- Python 3.8+
- Git

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/trangasaivarun/QuizMaster.git
   cd QuizMaster
   ```

2. **Set up the Database:**
   - Run the provided `init_db.py` file to create the `quizmaster.db` SQLite database and necessary tables.
     ```bash
     python init_db.py
     ```
   - This will automatically create an admin user: `admin@quizmaster.com` (Password: `admin123`).

3. **Install Dependencies:**
   Create a virtual environment (optional but recommended) and install the required Python packages.
   ```bash
   pip install flask werkzeug
   ```

4. **Run the Application:**
   Start the Flask development server.
   ```bash
   python app.py
   ```
   The application will be accessible at `http://127.0.0.1:5000/`.

### Sample Questions
You can use the provided `sample_questions.txt` to quickly populate the database with some initial quiz content via the admin dashboard or by importing it directly if you write a script.

## Usage
1. Open your web browser and navigate to `http://127.0.0.1:5000/`.
2. Register for a new account or log in if you already have one.
3. Once logged in, you can start a new quiz from the dashboard.
4. Admins can access the designated admin dashboard to create, edit, or delete quiz questions and view user analytics.

## Project Structure
```text
QuizMaster/
│
├── app.py                  # Main Flask application file
├── schema.sql              # Database schema definition
├── sample_questions.txt    # Sample questions for population
├── static/                 # Static assets (CSS, JavaScript, images)
│   └── css/                
│       └── styles.css      # Custom styling
└── templates/              # HTML templates
    ├── index.html          # Login/Registration page
    ├── base.html           # Base template layout
    ├── dashboard.html      # User dashboard
    ├── admin_dashboard.html# Administrator interface
    └── ...                 # Other template files
```

## Contributing
Contributions are welcome! If you would like to improve QuizMaster, please follow these steps:
1. Fork the repository.
2. Create a new branch for your feature or bug fix (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m "Added a new feature"`).
4. Push to the branch (`git push origin feature-name`).
5. Open a Pull Request.


