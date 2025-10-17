# for vps [add these part to run in vps]

from flask import Flask, request, jsonify

    from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

@app.route('/dobby', methods=['POST', 'GET'])
def dobby():
    data = request.json
    question = data.get("question", "")
    answer = f"Dobby says: You asked '{question}'"
    return jsonify({"answer": answer})

def run_flask():
    app.run(host="0.0.0.0", port=3000)

threading.Thread(target=run_flask).start()  