let timer = 0 * 60;
let timerInterval;
let answered = false;
let currentAnswer = "";

function loadQuestion() {
    fetch(`/quiz/${assessmentType}`)
        .then(res => res.json())
        .then(data => {
            if (data.finished) {
                alert(`${assessmentType} Test Finished!`);
            
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


let selectedVoice = null;

// Load voices and pick a female voice once
function loadVoices() {
    const voices = window.speechSynthesis.getVoices();
    selectedVoice = voices.find(voice =>
        voice.lang === 'en-US' && /female|Samantha|Zira|Karen/i.test(voice.name)
    );
}

window.speechSynthesis.onvoiceschanged = loadVoices;

function speak(text) {
    const msg = new SpeechSynthesisUtterance(text);
    msg.lang = 'en-US';
    msg.pitch = 1.7;
    msg.rate = 1.0;

    if (selectedVoice) {
        msg.voice = selectedVoice;
    }

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

function updateTimer() {
    const minutes = Math.floor(timer / 60);
    const seconds = timer % 60;
    document.getElementById("timer").innerText = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    timer++;
}

