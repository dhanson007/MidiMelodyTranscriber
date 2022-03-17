$(document).ready(function () {
    $('goals').change(function () {
        sessionStorage.setItem('goal', $(this).val());
        $('goals').value(sessionStorage.getItem('goal'));
    });
});