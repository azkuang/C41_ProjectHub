(function () {
  document.querySelectorAll(".drop-zone").forEach((dropZone) => {
    const fileInput = dropZone.querySelector(".file-input");
    const browseButton = dropZone.querySelector(".browse-button");
    const dropFilename = dropZone.querySelector(".drop-filename");

    if (!fileInput) return;

    function showFilename() {
      if (fileInput.files.length > 0 && dropFilename) {
        dropFilename.textContent = fileInput.files[0].name;
      }
    }

    if (browseButton) {
      browseButton.addEventListener("click", () => fileInput.click());
    }
    fileInput.addEventListener("change", showFilename);

    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("dragover");
      });
    });

    dropZone.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        fileInput.files = files;
        showFilename();
      }
    });
  });
})();
