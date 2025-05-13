let timer = 5 * 60;
let timerInterval;
let answered = false;
let currentAnswer = "";

function updateTimer() {
    const minutes = Math.floor(timer / 60);
    const seconds = timer % 60;
    document.getElementById("timer").innerText = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    if (timer <= 0) {
        clearInterval(timerInterval);
        alert("Time's up!");
        // window.location.href = `/console/end/${patient_id}`;
        setInterval(openPage, 1000);
    }
    timer--;
}

function loadQuestion() {
    fetch(`/quiz/${assessmentType}`)
        .then(res => res.json())
        .then(data => {
            if (data.finished) {
                alert(`${assessmentType} Test Finished! Score: ${data.score}, Patient: ${patient_id}`);
                
                // Wait a short time then redirect once
                setTimeout(() => {
                    window.location.href = `/console/end/${patient_id}`;
                }, 1000);
                return;
            }

            // Load next question
            currentAnswer = "";
            document.getElementById("quiz-prompt").innerText = data.prompt;
            document.getElementById("up-img").src = data.images.up;
            document.getElementById("down-img").src = data.images.down;
            document.getElementById("left-img").src = data.images.left;
            document.getElementById("right-img").src = data.images.right;
            speak(data.prompt);
        })
        .catch(error => {
            console.error("Error loading question:", error);
        });

    console.log("Loading question...");
}


function speak(text) {
    const msg = new SpeechSynthesisUtterance(text);
    msg.lang = 'en-US';
    window.speechSynthesis.speak(msg);
}

function openPage() {
    window.location.href = `/console/patient/${patient_id}`;
    return;
}

function pollPrediction() {
    if (answered) return;

    fetch("/get_prediction")
        .then(response => response.json())
        .then(data => {
            const word = data.word;
            if (word && !answered) {
                answered = true;
                submitAnswer(word);
            }
        });
}

setInterval(pollPrediction, 1000);

function submitAnswer(word) {
    fetch(`/submit_answer/${assessmentType}`, {
        method: "POST",
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({word})
    })
    .then(res => res.json())
    .then(data => {
        const scoreElem = document.getElementById("score");
        scoreElem.innerText = `Score: ${data.score}`;
        answered = false;
        loadQuestion();
    })
    .catch(error => {
        console.error("Error submitting answer:", error);
        answered = false;  // Important to unlock prediction again
    });
}


document.addEventListener("DOMContentLoaded", () => {
    loadQuestion();
    timerInterval = setInterval(updateTimer, 1000);
});

