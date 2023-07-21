from flask import Flask, render_template, request, session, redirect, jsonify, url_for
from flask_mysqldb import MySQL
from flask_socketio import SocketIO, emit
import openai

app = Flask(__name__)
socketio = SocketIO(app)

openai.api_key = "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"
# 设置MySQL数据库连接
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'lxmqi663393'
app.config['MYSQL_DB'] = 'gpt_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# 设置密钥
app.secret_key = 'aldjfqnlfddg'

score=0
number=0

@app.route('/')
def index():
     if 'username' in session:
        session['logged_in'] = True
        return render_template('index.html', logged_in=True)
     else:
        return render_template('index.html')

def get_user_score(username):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT score FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    score = result['score'] if result else 0
    return score

def get_user_number(username):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT number FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    number = result['number'] if result else 0
    return number

@app.route('/stats', methods=['GET'])
def stats():
    if 'username' in session:
        username = session['username']
        # 获取最新的得分和回答次数
        score = get_user_score(username)
        number = get_user_number(username)
        # 返回 JSON 数据
        return jsonify(score=score, number=number)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        mysql.connection.commit()
        cursor.close()
        session['username'] = username
        username = session['username']
        score = get_user_score(username)
        number = get_user_number(username)
        redirect_url = url_for('index', score=score, numbert=number, logged_in=True)
        return redirect(redirect_url)
    else:
         return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        result = cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        
        if result > 0:
            session['username'] = username
            username = session['username']
            score = get_user_score(username)
            number = get_user_number(username)
            redirect_url = url_for('index', score=score, numbert=number, logged_in=True)
            return redirect(redirect_url)
        else:
            return ("登录失败，请检查用户名和密码。")
           
    else:
          return render_template('index.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect('/')

# 聊天历史记录列表
chat_history = []

# 设置要发送的历史记录数量
history_limit = 20

@app.route('/clear_history', methods=['POST'])
def clear_history():
    #清空历史记录
    chat_history.clear()
    return jsonify({"status": "success"})
    
@app.route('/send_message', methods=['POST'])
def send_message():
    
    message = request.form['message']
    
    # 将用户消息添加到聊天历史记录
    chat_history.append({"role": "user", "content": message})
    
    # 获取一定数量的历史记录
    limited_history = chat_history[-history_limit:]

    # 包含历史记录的消息列表
    messages = [{"role": "system", "content": "You are currently an encyclopedia knowledge reviewer, You have prepared 1,000 encyclopedic knowledge questions without repetition, asking one question in Chinese each time and providing users with ABC options. These three options should be displayed in a new line.The correctness judgment is made after the user answers each question. If the user answers correctly, the symbol must be given in the evaluation: ✅， If the user's answer is incorrect, the symbol must be given in the evaluation: ❌。 After evaluation, the next question will be raised in a new row. When the user says' start ', you start asking the first question, and each question should have a number.When the user say' stop ',you stop ask the question."}] + limited_history

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        #stream=True,
        messages=messages
    )
    
    # 将AI回复添加到聊天历史记录
    chat_history.append({"role": "assistant", "content": response.choices[0].message.content})

    #如果消息中带有✅，则将用户得分加1,只要有问题，次数加1
    if "✅" in response.choices[0].message.content or "❌" in response.choices[0].message.content:
            cursor = mysql.connection.cursor()
            cursor.execute("UPDATE users SET number = number + 1 WHERE username = %s", (session['username'],))
            if "✅" in response.choices[0].message.content:
              cursor.execute("UPDATE users SET score = score + 1 WHERE username = %s", (session['username'],))
            mysql.connection.commit()
            cursor.close()


    return jsonify({"response": response.choices[0].message.content})


if __name__ == '__main__':
    app.run(debug=True)
