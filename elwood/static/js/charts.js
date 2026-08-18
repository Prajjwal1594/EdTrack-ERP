/**
 * charts.js — Student Progress Visualization
 * Logic for Radar (Holistic) and Line (Trend) charts using Chart.js
 */

function initHolisticRadar(canvasId, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Academic', 'Leadership', 'Discipline', 'Communication', 'Teamwork', 'Co-Curricular'],
            datasets: [{
                label: 'Student Balance',
                data: [
                    data.avg_grade, 
                    data.soft_skills.leadership * 10, 
                    data.soft_skills.discipline * 10,
                    data.soft_skills.communication * 10, 
                    data.soft_skills.teamwork * 10,
                    data.attendance_pct
                ],
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgb(54, 162, 235)',
                pointBackgroundColor: 'rgb(54, 162, 235)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            elements: {
                line: { borderWidth: 3 }
            },
            scales: {
                r: {
                    angleLines: { display: false },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            }
        }
    });
}

function initPerformanceTrend(canvasId, trendData) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: trendData.map(d => d.date),
            datasets: [{
                label: 'Holistic Score',
                data: trendData.map(d => d.score),
                fill: true,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

/**
 * AI Chat Assistant Logic
 */
async function sendChatMessage(studentId, message) {
    const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: studentId, message: message })
    });
    return await response.json();
}
