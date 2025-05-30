lines = ["Here's some stuff about me!", "I'm still waiting...", "Whenever you're ready :P", "I’ve got time. Infinite, actually.", "I've got a bad feeling about this...", "01001000 01101001"];

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function headType() {
    for (i of lines) {
        let l = "";
        for (let j = 0; j < i.length; j++) {
            await sleep(150);
            l = l.substring(0, l.length - 1) + i[j] + "|";
            document.getElementById("header").innerHTML = l;
        }
        let k = 0;
        while (k < 7) {
            document.getElementById("header").innerHTML = l.substring(0, l.length - 1) + " ";
            await sleep(500);
            document.getElementById("header").innerHTML = l;
            await sleep(500)
            k++;
        }
        for (let j = i.length - 1; j >= 0; j--) {
            await sleep(150);
            l = l.substring(0, j) + "|";
            document.getElementById("header").innerHTML = l;
        }
        await sleep(100);
    }
}

async function completeHead() { while (true) { await headType() }; }

completeHead();