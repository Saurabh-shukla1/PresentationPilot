<?php
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $name = htmlspecialchars($_POST['name']);
    $surname = htmlspecialchars($_POST['surname']);
    $gender = htmlspecialchars($_POST['gender']);
    $email = htmlspecialchars($_POST['email']);

    // Email details
    $to = 'sanjaysonar741@gmail.com';
    $subject = 'New Contact Form Submission';
    $message = "You have received a new contact form submission:\n\n" .
               "Name: $name\n" .
               "Surname: $surname\n" .
               "Gender: $gender\n" .
               "Email: $email\n";

    $headers = "From: no-reply@yourdomain.com\r\n";
    $headers .= "Reply-To: $email\r\n";

    // Send email
    if (mail($to, $subject, $message, $headers)) {
        echo "Thank you for your submission! We'll get back to you soon.";
    } else {
        echo "There was an issue sending your message. Please try again.";
    }
}
?>
