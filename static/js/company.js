function showRegister(){
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("registerForm").style.display = "block";

    // CHANGE IMAGE
    document.getElementById("authImage").src = "../static/images/Signup.png";
}

function showLogin(){
    document.getElementById("loginForm").style.display = "block";
    document.getElementById("registerForm").style.display = "none";

    // CHANGE IMAGE
    document.getElementById("authImage").src = "../static/images/login.jpg";
}