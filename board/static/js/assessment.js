// assessment.js

document.addEventListener("DOMContentLoaded", function () {
    const patientSelect = document.getElementById("patientSelect");
    const startAssessmentBtn = document.getElementById("startAssessmentBtn");

    // Function to send the result to the server
    async function saveResult() {
        const patientId = patientSelect.value;
        const answers = getTestAnswers();  // Function to gather answers from the user
        const score = calculateScore(answers);  // Calculate score based on answers
        const duration = calculateDuration();  // Duration of the test in seconds

        if (!patientId || !answers || score === null) {
            alert("Please complete the assessment first.");
            return;
        }

        // Send the result to the server
        const response = await fetch("/save_peabody_result", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                patient_id: patientId,
                answers: answers,
                score: score,
                duration: duration
            })
        });

        const data = await response.json();
        
        if (data.success) {
            alert("Assessment result saved successfully!");
        } else {
            alert("Failed to save assessment results. Please try again.");
        }
    }

    // Dummy functions for demonstration purposes, replace with actual implementation
    function getTestAnswers() {
        return [
            { question: 1, answer: "A" },
            { question: 2, answer: "C" }
        ];
    }

    function calculateScore(answers) {
        return answers.length;
    }

    function calculateDuration() {
        return 120;
    }

    // Show the 'Start Assessment' button once a patient is selected
    patientSelect.addEventListener("change", function() {
        if (patientSelect.value) {
            startAssessmentBtn.classList.remove("d-none");
        } else {
            startAssessmentBtn.classList.add("d-none");
        }
    });
});
