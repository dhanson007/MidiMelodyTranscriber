if (sessionStorage.getItem('goal') === null) {
    sessionStorage.setItem('goal', "sleep");
    document.write("Sleep");
}
else {
    if (sessionStorage.getItem('goal') === "sleep") {
        document.write("Sleep");
    } else if (sessionStorage.getItem('goal') === "med") {
        document.write("Meditation");
    } else if (sessionStorage.getItem('goal') === "stress") {
        document.write("Stress");
    } else if (sessionStorage.getItem('goal') === "focus") {
        document.write("Focus");
    } else if (sessionStorage.getItem('goal') === "mem") {
        document.write("Memory");
    }
}