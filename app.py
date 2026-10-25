<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AI Detective Game</title>
    <style>
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
            background-color: #111;
            color: #eee;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            overflow: hidden;
        }
        #game-container {
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            max-width: 800px;
            margin: 0 auto;
        }
        #top-area {
            flex: 0 0 35%;
            background-color: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            border-bottom: 2px solid #333;
            overflow: hidden;
            position: relative;
        }
        #scene-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: opacity 0.5s ease;
        }
        #image-loading {
            position: absolute;
            color: #aaa;
            font-size: 12px;
            background: rgba(0,0,0,0.6);
            padding: 4px 8px;
            border-radius: 4px;
            display: none;
        }
        #bottom-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background-color: #1a1a1a;
            padding: 10px;
            overflow: hidden;
        }
        #dialogue-box {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 10px;
            line-height: 1.5;
            font-size: 14px;
        }
        .ai-message {
            margin-bottom: 10px;
            color: #fff;
        }
        .player-message {
            margin-bottom: 10px;
            text-align: right;
            color: #8ab4f8;
        }
        #input-area {
            display: flex;
            gap: 8px;
            flex-shrink: 0;
            padding-bottom: env(safe-area-inset-bottom);
        }
        #user-input {
            flex: 1;
            padding: 10px;
            background-color: #2a2a2a;
            border: 1px solid #444;
            color: #fff;
            border-radius: 4px;
            font-size: 16px;
        }
        #submit-btn {
            padding: 10px 16px;
            background-color: #8ab4f8;
            border: none;
            color: #000;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            flex-shrink: 0;
        }
    </style>
</head>
<body>

<div id="game-container">
    <div id="top-area">
        <img id="scene-image" src="https://image.pollinations.ai/prompt/Victorian%20mansion%20lounge%20mystery%20dark%20atmospheric%20oil%20painting" alt="Scene">
        <div id="image-loading">画像生成中...</div>
    </div>
    <div id="bottom-area">
        <div id="dialogue-box">
            <div class="ai-message">事件が発生しました。スタイルズ荘のラウンジで調査を開始してください。</div>
        </div>
        <div id="input-area">
            <input type="text" id="user-input" placeholder="行動や質問を入力...">
            <button id="submit-btn" onclick="sendMessage()">送信</button>
        </div>
    </div>
</div>

<script>
    async function updateSceneImage(textForImage) {
        const imgElement = document.getElementById('scene-image');
        const loadingElement = document.getElementById('image-loading');
        
        loadingElement.style.display = 'block';
        
        // Geminiの返答テキストから簡単なプロンプトを構築
        const promptString = "Victorian mystery detective story scene, " + textForImage.substring(0, 150);
        const encodedPrompt = encodeURIComponent(promptString);
        
        // キャッシュによる画像更新の抑制を防ぐためランダムなシード値（seed）を付与
        const randomSeed = Math.floor(Math.random() * 10000);
        const imageUrl = `https://image.pollinations.ai/prompt/${encodedPrompt}?width=800&height=450&nologo=true&seed=${randomSeed}`;

        const newImg = new Image();
        newImg.src = imageUrl;
        newImg.onload = function() {
            imgElement.src = imageUrl;
            loadingElement.style.display = 'none';
        };
        newImg.onerror = function() {
            loadingElement.style.display = 'none';
        };
    }

    async function sendMessage() {
        const inputField = document.getElementById('user-input');
        const dialogueBox = document.getElementById('dialogue-box');
        const message = inputField.value.trim();

        if (message === "") return;

        const playerDiv = document.createElement('div');
        playerDiv.className = 'player-message';
        playerDiv.innerText = message;
        dialogueBox.appendChild(playerDiv);

        inputField.value = '';
        dialogueBox.scrollTop = dialogueBox.scrollHeight;

        const aiDiv = document.createElement('div');
        aiDiv.className = 'ai-message';
        aiDiv.innerText = "考え中...";
        dialogueBox.appendChild(aiDiv);
        dialogueBox.scrollTop = dialogueBox.scrollHeight;

        try {
            const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=YOUR_API_KEY", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    contents: [{
                        role: "user",
                        parts: [{ text: `あなたはAI探偵ゲームの進行役です。スタイルズ荘での殺人事件について、次のプレイヤーの発言に反応してください。プレイヤー: ${message}` }]
                    }],
                    systemInstruction: {
                        parts: [{ text: "あなたは探偵小説のゲームマスターです。常にテキストで状況を描写し、プレイヤーの調査に対して返答してください。" }]
                    }
                })
            });

            const data = await response.json();
            const replyText = data.candidates[0].content.parts[0].text;
            aiDiv.innerText = replyText;
            dialogueBox.scrollTop = dialogueBox.scrollHeight;

            // ★Geminiの返答（replyText）を渡して新しい場面画像を自動生成
            updateSceneImage(replyText);

        } catch (error) {
            console.error("Error:", error);
            aiDiv.innerText = "エラーが発生しました。APIキーを確認してください。";
        }
    }

    document.getElementById("user-input").addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            sendMessage();
        }
    });
</script>

</body>
</html>
