(function () {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const browseButton = document.getElementById("browse-button");
  const dropFilename = document.getElementById("drop-filename");

  if (!dropZone || !fileInput) return;

  function showFilename() {
    if (fileInput.files.length > 0) {
      dropFilename.textContent = fileInput.files[0].name;
    }
  }

  browseButton.addEventListener("click", () => fileInput.click());
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
})();
