from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import mysql.connector
import base64
import os
import uuid
import json
from datetime import datetime
import requests
from PIL import Image
import io
import clip
import torch
from transformers import CLIPProcessor, CLIPModel
import traceback
import google.generativeai as genai


app = Flask(__name__)
app.secret_key = 'grievance_chatbot_secret_key'  # Single secret key

# Configure session
app.config['SESSION_COOKIE_SECURE'] = False  # Changed to False for HTTP
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Changed back to Lax for HTTP
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cross-domain cookies

# Configure CORS with specific settings
CORS(app, 
    supports_credentials=True,
    resources={
        r"/*": {
            "origins": ["http://127.0.0.1:5500", "http://localhost:5500","*"],
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type"]
        }
    }
)

# Database Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "ashimonusql@0",
    "database": "grievance_db"
}

# OpenAI Configuration
genai.configure(api_key="AIzaSyBdKeckdj2w7tFj2Ue53N8XNJRW2RhhvqY")

# Load CLIP model for image verification
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)


# Initialize database tables
def init_db():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Create departments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    )
    """)
    
    # Create complaints table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ticket_number VARCHAR(20) NOT NULL UNIQUE,
        user_id INT NOT NULL,
        department_id INT NOT NULL,
        description TEXT NOT NULL,
        address TEXT NOT NULL,
        status ENUM('Pending', 'In Progress', 'Resolved') DEFAULT 'Pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        image_path VARCHAR(255),
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )
    """)
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL UNIQUE,
        phone VARCHAR(20)
    )
    """)
    
    # Create admins table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        department_id INT,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )
    """)
    
    # Insert default departments
    departments = [
        "Electrical", 
        "IT", 
        "Maintenance", 
        "Civil", 
        "Security", 
        "HR", 
        "Finance", 
        "Administration"
    ]
    
    for dept in departments:
        try:
            cursor.execute("INSERT INTO departments (name) VALUES (%s)", (dept,))
        except mysql.connector.errors.IntegrityError:
            # Department already exists
            pass
    
    conn.commit()
    cursor.close()
    conn.close()

# Initialize database on startup
init_db()

def classify_complaint(complaint_text):
    model = genai.GenerativeModel("gemini-2.0-flash")

    analysis_prompt = f"""As an AI complaint classifier, analyze this message and determine if it's a valid complaint:

    Message: {complaint_text}

    First determine if this is a valid complaint about government services/infrastructure.
    If it's not a clear complaint, respond with "casual".
    If it is a complaint, classify it into one of these departments:
    Administration, Civil, Education, Electrical, Finance, Health & Sanitation,
    HR, IT, Maintenance, Public Safety, Road & Transport, Security, Waste Management, Water

    Consider:
    1. Is this a specific issue or just casual conversation?
    2. Does it mention any concrete problems?
    3. Is there enough context to classify it?
    4. Which department would be most appropriate to handle this issue?

    Respond with ONLY ONE WORD: either "casual" or the department name."""

    response = model.generate_content(analysis_prompt)
    classified_dept = response.text.strip()

    # If classification is unclear or too vague, return casual
    if classified_dept.lower() == "casual" or not classified_dept:
        return "casual"
    return classified_dept

# Helper function to verify image relevance using CLIP
def verify_image_relevance(image_data, complaint_text):
    try:
        if not image_data:
            raise ValueError("No image data provided")

        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Process image and text with CLIP
        image_input = preprocess(image).unsqueeze(0).to(device)
        text = clip.tokenize([complaint_text]).to(device)
        
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            text_features = model.encode_text(text)
            
            # Normalize features
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            
            # Calculate similarity score
            similarity = (100.0 * image_features @ text_features.T).item()
        
        # Check if similarity score exceeds threshold
        return similarity > 25.0, similarity  # Threshold can be adjusted
    except Exception as e:
        print(f"Error in image verification: {str(e)}")
        return False, 0.0

@app.route('/api/submit_complaint', methods=['POST'])
def submit_complaint():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        description = data.get('complaint')
        address = data.get('address')  # Get address from request
        image_data = data.get('image')  # Base64-encoded image data

        # Generate a unique ticket number
        ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"

        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Check if the user exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            # Create a new user if they don't exist
            cursor.execute("""
                INSERT INTO users (name, email, phone)
                VALUES (%s, %s, %s)
            """, (name, email, phone))
            user_id = cursor.lastrowid  # Get the newly created user's ID
        else:
            user_id = user[0]  # Use the existing user's ID

        # Classify complaint to get department
        department_name = classify_complaint(description)
        cursor.execute("SELECT id FROM departments WHERE name = %s", (department_name,))
        department = cursor.fetchone()

        if not department:
            # If department not found, assign to default department (Administration)
            cursor.execute("SELECT id FROM departments WHERE name = 'Administration'")
            department = cursor.fetchone()

        department_id = department[0]

        # Handle image upload if present
        image_path = None
        if image_data:
            # Verify image relevance using CLIP
            is_relevant, similarity_score = verify_image_relevance(image_data, description)
            if not is_relevant:
                return jsonify({
                    "success": False,
                    "message": f"Irrelevant image attached. Similarity score: {similarity_score:.2f}. Complaint rejected."
                }), 400

            # Save the image if relevant
            try:
                image_bytes = base64.b64decode(image_data.split(',')[1])
                os.makedirs("uploads", exist_ok=True)
                image_path = f"uploads/{ticket_number}.jpg"
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
            except Exception as e:
                print("Image Processing Error:", str(e))
                image_path = None

        # Insert the complaint into the database
        cursor.execute("""
            INSERT INTO complaints (ticket_number, user_id, department_id, description, address, image_path)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ticket_number, user_id, department_id, description, address, image_path))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Complaint submitted successfully.",
            "ticket_number": ticket_number,
            "department": department_name
        })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"success": False, "message": "An error occurred while submitting the complaint."}), 500

# Route to track complaint status
@app.route('/api/track_complaint', methods=['POST', 'OPTIONS'])
def track_complaint():
    try:
        # ✅ Handle CORS Preflight Request
        if request.method == "OPTIONS":  
            response = jsonify({"message": "CORS Preflight OK"})
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response, 200

        # ✅ Ensure request contains JSON data
        if not request.is_json:
            return jsonify({"success": False, "message": "Invalid request format"}), 400

        data = request.json
        ticket_number = data.get('ticket_number')

        if not ticket_number:
            return jsonify({"success": False, "message": "Ticket number is required"}), 400

        # ✅ Connect to MySQL database
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
        except mysql.connector.Error as db_error:
            print("Database Connection Error:", db_error)
            return jsonify({"success": False, "message": "Database connection failed"}), 500

        # ✅ Fetch complaint details
        cursor.execute("""
            SELECT c.ticket_number, c.description, c.status, c.created_at, c.address,
                   c.updated_at, COALESCE(d.name, 'Unknown') as department
            FROM complaints c
            LEFT JOIN departments d ON c.department_id = d.id
            WHERE c.ticket_number = %s
        """, (ticket_number,))

        complaint = cursor.fetchone()
        cursor.close()
        conn.close()

        # ✅ If complaint is found, return formatted response
        if complaint:
            complaint['created_at'] = complaint['created_at'].isoformat()
            complaint['updated_at'] = complaint['updated_at'].isoformat()
            return jsonify({"success": True, "complaint": complaint})

        # ✅ If ticket not found
        return jsonify({"success": False, "message": "Ticket number not found. Please check and try again."}), 404

    except Exception as e:
        print("Error:", e)  # Debugging
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500

# Admin login route
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # Validate admin credentials
    cursor.execute("""
        SELECT a.id, a.username, a.department_id, d.name AS department_name
        FROM admins a
        LEFT JOIN departments d ON a.department_id = d.id
        WHERE a.username = %s AND a.password = %s
    """, (username, password))
    admin = cursor.fetchone()

    if admin:
        session['admin_id'] = admin['id']
        session['admin_username'] = admin['username']
        session['department_name'] = admin['department_name']  # Store department name in the session
        session.permanent = True  # Make the session persistent
        return jsonify({"success": True, "message": "Login successful"})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

# Route to get all complaints for admin
@app.route('/api/admin/complaints', methods=['GET'])
def get_all_complaints():
    if 'admin_id' not in session:
        return jsonify({"success": False, "message": "Please login first"})
    
    department = request.args.get('department')
    status = request.args.get('status')
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT c.id, c.ticket_number, c.description, c.status, 
               c.created_at, c.updated_at, d.name as department,
               u.name as user_name, u.email as user_email
        FROM complaints c
        JOIN departments d ON c.department_id = d.id
        JOIN users u ON c.user_id = u.id
        WHERE 1=1
    """
    params = []
    
    if department:
        query += " AND d.name = %s"
        params.append(department)
    
    if status:
        query += " AND c.status = %s"
        params.append(status)
    
    query += " ORDER BY c.created_at DESC"
    
    try:
        cursor.execute(query, params)
        complaints = cursor.fetchall()
        
        # Format dates for JSON
        for complaint in complaints:
            complaint['created_at'] = complaint['created_at'].isoformat()
            complaint['updated_at'] = complaint['updated_at'].isoformat()
        
        return jsonify({"success": True, "complaints": complaints})
    except Exception as e:
        print("Error fetching complaints:", str(e))
        return jsonify({"success": False, "message": "Error fetching complaints"}), 500
    finally:
        cursor.close()
        conn.close()

# Route to update complaint status
@app.route('/api/admin/update_status', methods=['POST'])
def update_complaint_status():
    if 'admin_id' not in session:
        return jsonify({"success": False, "message": "Please login first"})
    
    data = request.json
    complaint_id = data.get('complaint_id')
    new_status = data.get('status')
    
    if new_status not in ['Pending', 'In Progress', 'Resolved']:
        return jsonify({
            "success": False,
            "message": "Invalid status. Status must be Pending, In Progress, or Resolved."
        })
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE complaints SET status = %s WHERE id = %s",
        (new_status, complaint_id)
    )
    
    conn.commit()
    
    # Get user email for notification
    cursor.execute("""
        SELECT u.email, c.ticket_number
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        WHERE c.id = %s
    """, (complaint_id,))
    
    result = cursor.fetchone()
    user_email = result[0]
    ticket_number = result[1]
    
    cursor.close()
    conn.close()
    
    # TODO: Send email notification (implement actual email sending)
    # For now, just logging
    print(f"Status update notification would be sent to {user_email} for ticket {ticket_number}")
    
    return jsonify({
        "success": True,
        "message": f"Complaint status updated to {new_status}"
    })

# Route to get departments
@app.route('/api/admin/departments', methods=['GET'])
def get_departments():
    if 'admin_id' not in session:
        return jsonify({"success": False, "message": "Please login first"})

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, name FROM departments")
        departments = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({"success": True, "departments": departments})
    except Exception as e:
        print("Error fetching departments:", str(e))
        return jsonify({"success": False, "message": "Internal Server Error"})

@app.route('/api/admin/complaints/<int:complaint_id>', methods=['GET'])
def get_complaint_details(complaint_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Updated query to remove latitude and longitude
        cursor.execute("""
            SELECT c.id, c.ticket_number, c.description, c.status, 
                   c.created_at, c.updated_at, c.image_path,
                   c.address,
                   d.name AS department, u.name AS user_name, 
                   u.email AS user_email
            FROM complaints c
            JOIN departments d ON c.department_id = d.id
            JOIN users u ON c.user_id = u.id
            WHERE c.id = %s
        """, (complaint_id,))
        complaint = cursor.fetchone()

        cursor.close()
        conn.close()

        if not complaint:
            return jsonify({"success": False, "message": "Complaint not found"}), 404

        # Format dates for JSON
        complaint['created_at'] = complaint['created_at'].isoformat()
        complaint['updated_at'] = complaint['updated_at'].isoformat()

        return jsonify({"success": True, "complaint": complaint})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"success": False, "message": "An error occurred while fetching complaint details"}), 500

@app.route('/api/chat', methods=['POST'])
def chat_with_llm():
    try:
        data = request.json
        user_message = data.get('message')

        if not user_message:
            return jsonify({"success": False, "message": "Message is required"}), 400

        # Use Gemini to analyze the message and generate response
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        analysis_prompt = f"""You are GrieveBuddy, a friendly and helpful government grievance chatbot assistant. 
        Analyze the following user message and respond naturally while maintaining professionalism:
        User message: {user_message}

        If the message is:
        - A greeting: Respond warmly and ask how you can help with their grievance
        - A thank you: Acknowledge graciously and offer further assistance
        - A follow-up question: Provide helpful guidance about the grievance process
        - A complaint: Identify the relevant department and guide them to submit formally
        - Casual chat: Politely redirect to grievance-related topics

        Available departments for complaints:
        Administration, Civil, Education, Electrical, Finance, Health & Sanitation, 
        HR, IT, Maintenance, Public Safety, Road & Transport, Security, Waste Management, Water

        Remember to:
        1. Keep responses conversational but professional
        2. Show empathy for grievances
        3. Guide users toward formal complaint submission
        4. Maintain context in follow-up responses

        Respond in this exact JSON format (no additional text):
        {{"type": "greeting|thanks|followup|complaint|casual", "reply": "your response here", "department": "department_name"}}"""

        response = model.generate_content(analysis_prompt)
        
        try:
            # Clean the response text
            clean_response = response.text.strip().replace('\n', '').replace('```json', '').replace('```', '')
            result = json.loads(clean_response)
            
            if result["type"] == "complaint":
                return jsonify({
                    "success": True,
                    "type": "complaint",
                    "department": result.get("department", "Administration"),
                    "message": result["reply"]
                })
            else:
                return jsonify({
                    "success": True,
                    "type": result["type"],
                    "reply": result["reply"]
                })
                
        except json.JSONDecodeError as e:
            print("JSON Parse Error:", e)
            return jsonify({
                "success": True,
                "type": "casual",
                "reply": "I apologize, but I'm having trouble understanding. Could you please rephrase that?"
            })

    except Exception as e:
        print("Error in chat_with_llm:", str(e))
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your message"
        }), 500

@app.route('/api/admin/reports', methods=['GET'])
def get_reports():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch statistics
        cursor.execute("""
            SELECT COUNT(*) AS total_complaints,
                   SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved_complaints,
                   SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending_complaints,
                   SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress_complaints
            FROM complaints
        """)
        statistics = cursor.fetchone()

        # Fetch chart data (example: complaints by department)
        cursor.execute("""
            SELECT d.name AS department, COUNT(*) AS total
            FROM complaints c
            JOIN departments d ON c.department_id = d.id
            GROUP BY d.name
        """)
        chart_data = cursor.fetchall()

        # Fetch status data for pie chart
        cursor.execute("""
            SELECT status, COUNT(*) AS count
            FROM complaints
            GROUP BY status
        """)
        status_data = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "statistics": statistics,
            "chartData": chart_data,
            "statusData": status_data  # Include status data for pie chart
        })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"success": False, "message": "An error occurred while fetching reports"}), 500

@app.route('/api/admin/session', methods=['GET'])
def validate_admin_session():
    if 'admin_id' in session:
        # Get admin info from database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.username, d.name as department_name 
            FROM admins a 
            LEFT JOIN departments d ON a.department_id = d.id 
            WHERE a.id = %s
        """, (session['admin_id'],))
        
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "admin_id": session['admin_id'],
            "admin_username": admin['username'],
            "department_name": admin['department_name']
        })
    else:
        return jsonify({"success": False, "message": "Admin session is not active"})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/uploads/<path:filename>')
def serve_image(filename):
    return send_from_directory('uploads', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
