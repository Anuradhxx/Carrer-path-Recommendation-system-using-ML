document.addEventListener("DOMContentLoaded", () => {

  // ===== PROGRESS DATA =====
  let progressData = JSON.parse(localStorage.getItem("progressData")) || [];
  const progressList = document.getElementById("progressList");

  function renderProgress() {
    progressList.innerHTML = "";

    if (progressData.length === 0) {
      progressList.innerHTML = `<p class="empty">No progress tracked yet. Start tracking your skills!</p>`;
      return;
    }

    progressData.forEach(item => {
      const div = document.createElement("div");
      div.classList.add("progress-item");

      div.innerHTML = `
        <div style="display:flex; justify-content:space-between;">
          <span>${item.skill}</span>
          <span>${item.progress}%</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width:${item.progress}%"></div>
        </div>
      `;

      progressList.appendChild(div);
    });
  }

  // Initial render
  renderProgress();

  // ===== ADD NEW PROGRESS =====
  const addBtn = document.getElementById("addProgressBtn");
  addBtn.addEventListener("click", () => {
    const skill = document.getElementById("skillInput").value.trim();
    const progress = parseInt(document.getElementById("progressInput").value);

    if (!skill || isNaN(progress) || progress < 0 || progress > 100) {
      alert("Enter valid skill and progress (0-100)");
      return;
    }

    // Update existing skill or add new
    const existing = progressData.find(item => item.skill === skill);
    if (existing) {
      existing.progress = progress;
    } else {
      progressData.push({ skill, progress });
    }

    // Save to localStorage
    localStorage.setItem("progressData", JSON.stringify(progressData));

    // Re-render
    renderProgress();

    // Clear inputs
    document.getElementById("skillInput").value = "";
    document.getElementById("progressInput").value = "";
  });

});