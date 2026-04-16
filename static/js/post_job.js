
    // Populate form for editing
    const editButtons = document.querySelectorAll('.editBtn');
    const form = document.getElementById('jobForm');
    const submitBtn = document.getElementById('submitBtn');

    editButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('job_id').value = btn.dataset.id;
            document.getElementById('title').value = btn.dataset.title;
            document.getElementById('description').value = btn.dataset.description;
            document.getElementById('location').value = btn.dataset.location;
            document.getElementById('salary').value = btn.dataset.salary;
            document.getElementById('job_type').value = btn.dataset.type;
            submitBtn.textContent = "Update Job";
            form.action = `/update_job/${btn.dataset.id}`;
        });
    });





