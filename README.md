# Grievance Redressal Chatbot

A comprehensive grievance redressal system with AI-powered chatbot support, image verification, and GPS location tracking.

## Features

- 🤖 AI-powered chatbot for initial complaint assessment
- 📸 Image upload with GPS location verification
- 🔍 CLIP-based image relevance verification
- 📊 Admin dashboard with complaint management
- 📈 Real-time analytics and reporting
- 🔐 Secure admin authentication
- 📱 Responsive design for both user and admin interfaces

## Tech Stack

### Backend
- Flask (Python web framework)
- MySQL Database
- Google Gemini AI for chatbot
- CLIP for image verification
- Geopy for location services

### Frontend
- HTML5
- CSS3
- JavaScript (Vanilla)
- Responsive Design

## Prerequisites

- Python 3.8+
- MySQL Server
- Google Cloud API Key (for Gemini AI)
- Modern web browser

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd GrievanceRedressalChatbot
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Unix/MacOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure MySQL:
- Create a database named `grievance_db`
- Update database configuration in `backendflask.py`:
```python
db_config = {
    "host": "localhost",
    "user": "your_username",
    "password": "your_password",
    "database": "grievance_db"
}
```

5. Configure Google Gemini AI:
- Get your API key from Google Cloud Console
- Update the API key in `backendflask.py`:
```python
genai.configure(api_key="your_api_key")
```

## Running the Application

1. Start the Flask server:
```bash
python backendflask.py
```

2. Open the application:
- User Interface: `http://localhost:5500/user/index.html`
- Admin Interface: `http://localhost:5500/admin/index.html`

## Project Structure

```
GrievanceRedressalChatbot/
├── backendflask.py          # Main Flask application
├── requirements.txt         # Python dependencies
├── uploads/                 # Uploaded complaint images
├── user/                   # User interface
│   ├── index.html
│   ├── styles.css
│   └── script.js
└── admin/                  # Admin interface
    ├── index.html
    ├── styles.css
    └── script.js
```

## Features in Detail

### User Interface
- Submit complaints with images
- Track complaint status
- Chat with AI assistant
- View complaint history

### Admin Interface
- Dashboard with analytics
- Complaint management
- Department-wise filtering
- Status updates
- User management

### AI Features
- Complaint classification
- Image relevance verification
- GPS location extraction
- Smart chatbot responses

## Security Features

- Secure session management
- CORS protection
- Input validation
- Image verification
- GPS location validation

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the maintainers. 