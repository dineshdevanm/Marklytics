from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

app = Flask(__name__)
app.secret_key = '8f42a73054b17afec2284c1ce7161b34c281df6f4b62db1895a62e5b4b1a2e3a'

client = MongoClient('mongodb://localhost:27017/')
db = client['student_dashboard_db']
users_collection = db['users']
data_collection = db['student_data']

# --- HELPER FUNCTIONS ---
def get_learner_categories(df):
    """Categorize students into Fast and Slow learners based on CGPA."""
    try:
        name_col = [col for col in df.columns if 'name' in str(col).lower()][0]
        reg_col = [col for col in df.columns if 'register number' in str(col).lower()][0]
        gpa_col = [col for col in df.columns if 'gpa' in str(col).lower() and 'cgpa' not in str(col).lower()][0]
        cgpa_col = [col for col in df.columns if 'cgpa' in str(col).lower()][0]

        # Convert CGPA to numeric to safely compare numbers
        df_clean = df.copy()
        df_clean[cgpa_col] = pd.to_numeric(df_clean[cgpa_col], errors='coerce')
        
        slow_df = df_clean[df_clean[cgpa_col] <= 6.5]
        fast_df = df_clean[df_clean[cgpa_col] >= 9.0]

        def format_records(sub_df):
            records = []
            for _, row in sub_df.iterrows():
                records.append({
                    'name': row[name_col],
                    'reg_no': row[reg_col],
                    'gpa': row[gpa_col],
                    'cgpa': row[cgpa_col]
                })
            return records

        return format_records(slow_df), format_records(fast_df)
    except Exception as e:
        print(f"Error categorizing learners: {e}")
        return [], []

def generate_gpa_chart(df, title):
    plt.figure(figsize=(8, 5))
    try:
        gpa_col = [col for col in df.columns if 'GPA' in col.upper() and 'CGPA' not in col.upper()][0] 
        sns.histplot(df[gpa_col].dropna(), kde=True, bins=10, color='skyblue')
        plt.title(title)
        plt.xlabel('GPA')
        plt.ylabel('Number of Students')
        sns.despine(top=True, right=True)
        plt.grid(False)
    except Exception as e:
        plt.text(0.5, 0.5, 'GPA Data Not Available', ha='center', va='center')
        plt.axis('off')

    plt.tight_layout()
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', transparent=True)
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()
    return plot_url

def generate_course_charts(df):
    course_charts = []
    grade_cols = [c for c in df.columns if 'grade obtained in' in str(c).lower()]
    fail_grades = ['U', 'F', 'RA', 'W']
    standard_grades = ['O', 'A+', 'A', 'B+', 'B', 'C', 'U']

    for col in grade_cols:
        grades = df[col].dropna().astype(str).str.strip().str.upper()
        if grades.empty: continue

        fail_count = grades.isin(fail_grades).sum()
        pass_count = len(grades) - fail_count
        grade_counts = grades.value_counts().reindex(standard_grades, fill_value=0)

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        if pass_count > 0 or fail_count > 0:
            axes[0].pie([pass_count, fail_count], labels=['Pass', 'Fail'], 
                        autopct='%1.1f%%', startangle=90, colors=['#4CAF50', '#F44336'])
        axes[0].set_title('Pass Percentage')
            
        sns.barplot(x=grade_counts.index, y=grade_counts.values, ax=axes[1], palette='viridis')
        axes[1].set_title('Grade Distribution')
        axes[1].set_xlabel('Grades')
        axes[1].set_ylabel('Student Count')
        
        for container in axes[1].containers:
            axes[1].bar_label(container)

        sns.despine(ax=axes[1], top=True, right=True)
        axes[1].grid(False)
        
        clean_name = str(col).lower().replace('grade obtained in', '').strip().upper()
        plt.suptitle(f'Course Analysis: {clean_name}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', transparent=True)
        img.seek(0)
        course_charts.append(base64.b64encode(img.getvalue()).decode('utf8'))
        plt.close()

    return course_charts

# --- ROUTES ---
@app.route('/')
def home():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users_collection.find_one({'username': username}):
            flash('Username already exists!')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        users_collection.insert_one({'username': username, 'password': hashed_password})
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files['dataFile']
        batch = request.form['batch']
        year = request.form['year']
        section = request.form['section']
        
        if file:
            if file.filename.endswith('.csv'): df = pd.read_csv(file)
            else: df = pd.read_excel(file)
            
            df = df.iloc[:40]
            
            columns_to_keep = []
            for col in df.columns:
                col_lower = str(col).lower().strip()
                if ('register number' in col_lower) or ('name' in col_lower) or \
                   ('gpa' in col_lower) or ('cgpa' in col_lower) or ('grade obtained' in col_lower): 
                    columns_to_keep.append(col)
                    
            df = df[columns_to_keep]
            
            try:
                reg_col = [c for c in df.columns if 'register number' in str(c).lower()][0]
                df = df.dropna(subset=[reg_col])
            except: pass
            
            df = df.where(pd.notnull(df), None)
            
            records = df.to_dict('records')
            for record in records:
                record['user_id'] = session['user_id']
                record['batch'] = batch
                record['year'] = year
                record['section'] = section
                
            data_collection.insert_many(records)
            
            gpa_chart = generate_gpa_chart(df, f"GPA Distribution - Batch {batch} | Sec {section} | Year {year}")
            course_charts = generate_course_charts(df)
            slow_learners, fast_learners = get_learner_categories(df)
            
            return render_template('upload.html', 
                                   gpa_chart=gpa_chart, 
                                   course_charts=course_charts,
                                   slow_learners=slow_learners,
                                   fast_learners=fast_learners,
                                   success=True)
            
    return render_template('upload.html')

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    batch_q = request.args.get('batch', '')
    year_q = request.args.get('year', '')
    section_q = request.args.get('section', '')
    
    query = {}
    if batch_q: query['batch'] = batch_q
    if year_q: query['year'] = year_q
    if section_q: query['section'] = section_q

    gpa_chart = None
    course_charts = []
    slow_learners = []
    fast_learners = []
    recent_labels = None
    
    if batch_q or year_q or section_q:
        cursor = data_collection.find(query)
        df = pd.DataFrame(list(cursor))
        if not df.empty:
            gpa_chart = generate_gpa_chart(df, f"Global Search: Batch {batch_q} | Year {year_q} | Sec {section_q}")
            course_charts = generate_course_charts(df)
            slow_learners, fast_learners = get_learner_categories(df)
        else:
            flash("No data found for this search.")
    else:
        latest_record = data_collection.find_one({}, sort=[('_id', -1)])
        
        if latest_record:
            r_batch = latest_record.get('batch')
            r_year = latest_record.get('year')
            r_section = latest_record.get('section')
            
            recent_cursor = data_collection.find({
                'batch': r_batch, 'year': r_year, 'section': r_section
            })
            df_recent = pd.DataFrame(list(recent_cursor))
            
            recent_labels = {'batch': r_batch, 'year': r_year, 'section': r_section}
            gpa_chart = generate_gpa_chart(df_recent, f"Overall GPA Distribution")
            course_charts = generate_course_charts(df_recent)
            slow_learners, fast_learners = get_learner_categories(df_recent)

    return render_template('dashboard.html', 
                           gpa_chart=gpa_chart, 
                           course_charts=course_charts,
                           slow_learners=slow_learners,
                           fast_learners=fast_learners,
                           recent_labels=recent_labels)

if __name__ == '__main__':
    app.run(debug=True)