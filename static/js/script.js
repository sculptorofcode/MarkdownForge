document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadBtn = document.getElementById('upload-button');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const markdownEditor = document.getElementById('markdown-editor');
    const markdownPreview = document.getElementById('markdown-preview');
    const clearBtn = document.getElementById('clear-btn');
    const exampleBtn = document.getElementById('example-btn');
    const markdownForm = document.getElementById('markdown-form');

    // Upload button functionality
    uploadBtn.addEventListener('click', function() {
        fileInput.click();
    });
    
    // Configure marked.js options
    marked.setOptions({
        breaks: true,
        gfm: true,
        headerIds: false,
        sanitize: false
    });
    
    // Function to update preview
    function updatePreview() {
        const markdown = markdownEditor.value;
        markdownPreview.innerHTML = marked.parse(markdown);
    }
    
    // File upload handling
    fileInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const file = this.files[0];
            fileInfo.innerHTML = `<i class="fas fa-check-circle"></i> Selected: <strong>${file.name}</strong>`;
            
            // Read file content
            const reader = new FileReader();
            reader.onload = function(e) {
                markdownEditor.value = e.target.result;
                updatePreview();
            };
            reader.readAsText(file);
        } else {
            fileInfo.innerHTML = '';
        }
    });
    
    // Editor events
    markdownEditor.addEventListener('input', updatePreview);
    
    // Clear button functionality
    clearBtn.addEventListener('click', function() {
        markdownEditor.value = '';
        fileInfo.innerHTML = '';
        fileInput.value = '';
        updatePreview();
    });
    
    // Example button functionality
    exampleBtn.addEventListener('click', function() {
        markdownEditor.value = `# Markdown Example

## Introduction

This is a sample document showing various markdown features that will convert beautifully to PDF.

## Formatting

You can write text in **bold**, *italic*, or ***bold and italic***. 

## Lists

### Unordered Lists

- Item 1
- Item 2
  - Nested item 1
  - Nested item 2
- Item 3

### Ordered Lists

1. First item
2. Second item
   1. Nested item 1
   2. Nested item 2
3. Third item

## Code

Inline code: \`console.log('Hello World!')\`

Code block:

\`\`\`javascript
function greet(name) {
  return 'Hello, ' + name + '!';
}

console.log(greet('World'));
\`\`\`

## Quotes

> This is a blockquote. It can span multiple lines and can contain *formatted* text.

## Tables

| Name | Type | Description |
|------|------|-------------|
| id | integer | Unique identifier |
| name | string | User's name |
| email | string | User's email address |
`;
        updatePreview();
    });
    
    // AJAX Form submission handling
    markdownForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Display loading state
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Converting...';
        submitBtn.disabled = true;
        
        // Check if there's content to convert
        if (!markdownEditor.value.trim() && (!fileInput.files || !fileInput.files[0])) {
            alert('Please enter some markdown text or upload a file');
            submitBtn.innerHTML = originalBtnText;
            submitBtn.disabled = false;
            return;
        }
        
        // Prepare form data
        const formData = new FormData();
        formData.append('markdown-text', markdownEditor.value);
        
        // If file is selected, add it to form data
        let endpoint = '/convert_text';
        if (fileInput.files && fileInput.files[0]) {
            formData.append('file', fileInput.files[0]);
            endpoint = '/convert';
        }
        
        try {
            console.log('Sending request to:', endpoint);
            // Send AJAX request using axios
            const response = await axios.post(endpoint, formData, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'multipart/form-data'
                },
                responseType: 'blob'
            });
            console.log('Response received:', response);
            
            // Get the filename from Content-Disposition header if available
            let filename = 'document.pdf';
            const disposition = response.headers['content-disposition'];
            if (disposition && disposition.includes('filename=')) {
                const filenameMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            } else if (fileInput.files && fileInput.files[0]) {
                filename = fileInput.files[0].name.replace(/\.[^/.]+$/, '') + '.pdf';
            }
            
            // Create a download link for the PDF
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            
            document.body.appendChild(a);
            a.click();
            
            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error:', error);
            alert(error.response?.data?.error || 'An error occurred during conversion. Please try again.');
        } finally {
            // Reset button state
            submitBtn.innerHTML = originalBtnText;
            submitBtn.disabled = false;
        }
    });
    
    // Initialize preview on page load
    window.addEventListener('load', function() {
        if (markdownEditor.value.trim() === '') {
            exampleBtn.click();
        } else {
            updatePreview();
        }
    });
});