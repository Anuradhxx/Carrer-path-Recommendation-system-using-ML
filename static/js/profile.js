document.getElementById("addProgressBtn").addEventListener("click", () => {
    const skill = document.getElementById("skillInput").value.trim();
    const progress = document.getElementById("progressInput").value;

    if (!skill || progress < 0 || progress > 100) {
        alert("Enter valid data");
        return;
    }

    fetch('/add_progress', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `skill=${skill}&progress=${progress}`
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            location.reload();
        }
    });
});