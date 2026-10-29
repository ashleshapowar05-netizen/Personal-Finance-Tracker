console.log("Personal Finance Dashboard Loaded");


document.addEventListener(
    "DOMContentLoaded",
    function () {

        const dateInputs =
            document.querySelectorAll(
                "input[type='date']"
            );


        dateInputs.forEach(
            function (input) {

                if (!input.value) {

                    const today =
                        new Date()
                        .toISOString()
                        .split("T")[0];

                    input.value = today;

                }

            }
        );

    }
);