$(document).ready(function () {
    $("#openNav").click(function () {
        $(".sidebar").toggleClass("animate-toggle-button");
        $("#openNav").toggleClass("animate-toggle-button");
    });
    $("#openNav").click(function () {
        $("#openNav").toggleClass("animate-toggle");
    });
});
