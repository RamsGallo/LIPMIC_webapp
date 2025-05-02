let currentAnswer = "";
let timer = 20 * 60; // 20 minutes
let timerInterval;
let isListening = false;

function updateTimer() {
    const minutes = Math.floor(timer / 60);
    const seconds = timer % 60;
    document.getElementById("timer").innerText = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    if (timer <= 0) {
        clearInterval(timerInterval);
        alert("Time's up!");
    }
    timer--;
}

function loadQuestion() {
    fetch("/quiz")
        .then(res => res.json())
        .then(data => {
            if (data.finished) {
                alert(`Test Finished! Your score: ${data.score}`);
                return;
            }
            currentAnswer = ""; // reset
            document.getElementById("quiz-prompt").innerText = data.prompt;
            document.getElementById("up-img").src = data.images.up;
            document.getElementById("down-img").src = data.images.down;
            document.getElementById("left-img").src = data.images.left;
            document.getElementById("right-img").src = data.images.right;

            speak(data.prompt);
        });
}

function speak(text) {
    const msg = new SpeechSynthesisUtterance(text);
    msg.lang = 'en-US';
    window.speechSynthesis.speak(msg);
}

let answered = false;

function pollPrediction() {
  if (answered) return; // Prevent multiple submissions

  fetch("/get_prediction")
    .then(response => response.json())
    .then(data => {
      const word = data.word;
      if (word && !answered) {
        answered = true;
        submitAnswer(word);  // Your AJAX submit logic
      }
    });
}

setInterval(pollPrediction, 1000);  // Or adjust interval as needed

function submitAnswer(word) {
    fetch("/submit_answer", {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({word})
    })
    .then(res => res.json())
    .then(data => {
        if (data.correct) {
            const scoreElem = document.getElementById("score");
            const currentScore = parseInt(scoreElem.innerText.split(': ')[1]);
            scoreElem.innerText = `Score: ${currentScore + 1}`;
        }
        // Reset prediction flags and allow new predictions
        answered = false;  // <-- Ready for next question
        isListening = false;
        loadQuestion();    // Move to next item
    });
}


document.addEventListener("DOMContentLoaded", () => {
    loadQuestion();
    timerInterval = setInterval(updateTimer, 1000);
});

