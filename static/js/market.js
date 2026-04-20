const raw = document.getElementById("data-script").textContent;
const parsed = JSON.parse(raw);

const salaryTrend = parsed.salaryTrend || [];
const topSkills = parsed.topSkills || [];


const years = salaryTrend.map(x => x[0]);
const salaries = salaryTrend.map(x => x[1]);

Chart.defaults.font.family = "Satoshi, sans-serif";
Chart.defaults.color = "#666666"; 

new Chart(document.getElementById("salaryChart"), {
    type: "line",
    data: {
        labels: years,
        datasets: [{
            label: "Salary",
            data: salaries,
            borderColor: "#f97316",
            backgroundColor: "rgba(249, 116, 22, 0.14)",
            tension: 0.4,
            borderWidth: 3,
            pointRadius: 5,
            pointBackgroundColor: "#fff",
            pointBorderColor: "#f97316"
        }]
    },
    options: {
        plugins: {
            legend: {
                labels: {
                    color: "#475569",
                    font: { size: 14, weight: "500" }
                }
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: {
                    color: "#334c6e",
                    font: { size: 14 }
                }
            },
            y: {
                grid: {
                    color: "rgba(0, 0, 0, 0.15)"
                },
                ticks: {
                    color: "#31425b",
                    font: { size: 15 }
                }
            }
        }
    }
});


const skills = topSkills.map(x => x[0]);
const counts = topSkills.map(x => x[1]);

new Chart(document.getElementById("skillsChart"), {
    type: "bar",
    data: {
        labels: skills,
        datasets: [{
            label: "Demand",
            data: counts,
            backgroundColor: "#1c6b42",
            borderRadius: 8,
            barThickness: 90
        }]
    },
    options: {
        plugins: {
            legend: {
                labels: {
                    color: "#475569",
                    font: { size: 14 }
                }
            }
        },
        scales: {
            x: {
                grid: {
                     display: false
                     },
                ticks: {
                    color: "#242b36",
                    font: { size: 14 }
                }
            },
            y: {
                beginAtZero: true,
                grid: {
                    color: "rgba(109, 105, 105, 0.39)"
                },
                ticks: {
                    color: "#242b36",
                    font: { size: 15 }
                }
            }
        }
    }
});