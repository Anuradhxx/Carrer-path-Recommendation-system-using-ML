document.getElementById("addProgressBtn").addEventListener("click", () => {

    const skill_id = document.getElementById("skillSelect").value;
    const progress = parseInt(document.getElementById("progressInput").value);

    if (!skill_id || isNaN(progress) || progress < 0 || progress > 100) {
        alert("Enter valid data");
        return;
    }

    fetch('/add_progress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `skill_id=${skill_id}&progress=${progress}`
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            location.reload();
        }
    });
});