const rawData = document.getElementById("skills-data").textContent;
const skillsData = JSON.parse(rawData);

document.addEventListener("DOMContentLoaded", () => {
    skillsData.forEach(s => renderSkill(s));
    updateCount();
});

function renderSkill(skill) {
    const container = skill.type === "technical"
        ? document.getElementById("techList")
        : document.getElementById("softList");

    const div = document.createElement("div");
    div.className = "skill";
    div.id = "skill-" + skill.id;

    div.innerHTML = `
        <div>
            <strong>${skill.name}</strong>
            <span class="tag">${skill.proficiency}</span>
        </div>
        <span class="delete" onclick="deleteSkill(${skill.id})">Delete</span>
    `;

    container.appendChild(div);
}

function addSkill() {
    const name = document.getElementById("skillName").value.trim();
    const type = document.getElementById("skillType").value;
    const prof = document.getElementById("proficiency").value;

    // if (!name || name.length < 2) {
    //     alert("Invalid skill");
    //     return;
    // }

    if (!name || name.trim() === "") {
    alert("Please enter a skill");
    return;
}

const formData = new URLSearchParams();
formData.append("skill_name", name);
formData.append("skill_type", type);
formData.append("proficiency", prof);

fetch('/add_skill', {
    method: 'POST',
    body: formData
})
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            renderSkill({ id: data.id, name, type, proficiency: prof });
            updateCount();
            document.getElementById("skillName").value = "";
        } else {
            alert(data.message);
        }
    });
}

function deleteSkill(id) {
    fetch(`/delete_skill/${id}`)
    .then(() => {
        document.getElementById("skill-" + id).remove();
        updateCount();
    });
}

function updateCount() {
    const total =
        document.getElementById("techList").children.length +
        document.getElementById("softList").children.length;

    document.getElementById("totalCount").innerText = total;
}
