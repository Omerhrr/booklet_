/**
 * Main JavaScript for Booklet ERP
 */

// HTMX configuration
document.body.addEventListener('htmx:configRequest', function(event) {
    // Add CSRF token to all HTMX requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (csrfToken) {
        event.detail.headers['X-CSRFToken'] = csrfToken;
    }
});

// Show toast notification
function showToast(message, type = 'success') {
    window.dispatchEvent(new CustomEvent('show-toast', {
        detail: { message, type }
    }));
}

// Format currency
function formatCurrency(amount, symbol = '$') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount).replace('$', symbol);
}

// Format date
function formatDate(dateString, format = 'short') {
    const date = new Date(dateString);
    const options = format === 'long' 
        ? { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }
        : { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

// Confirm dialog
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Handle form errors
function handleFormErrors(form, errors) {
    // Clear previous errors
    form.querySelectorAll('.error-message').forEach(el => el.remove());
    form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    
    // Add new errors
    for (const [field, messages] of Object.entries(errors)) {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.classList.add('error');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message text-red-500 text-sm mt-1';
            errorDiv.textContent = messages.join(', ');
            input.parentNode.appendChild(errorDiv);
        }
    }
}

// Initialize dropdowns
function initDropdowns() {
    document.querySelectorAll('[data-dropdown-toggle]').forEach(button => {
        const dropdownId = button.getAttribute('data-dropdown-toggle');
        const dropdown = document.getElementById(dropdownId);
        
        if (dropdown) {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                dropdown.classList.toggle('hidden');
            });
        }
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown-menu').forEach(dropdown => {
            dropdown.classList.add('hidden');
        });
    });
}

// Initialize modals
function initModals() {
    document.querySelectorAll('[data-modal-toggle]').forEach(button => {
        const modalId = button.getAttribute('data-modal-toggle');
        const modal = document.getElementById(modalId);
        
        if (modal) {
            button.addEventListener('click', () => {
                modal.classList.toggle('hidden');
            });
        }
    });
    
    // Close modal when clicking backdrop
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', () => {
            backdrop.querySelector('.modal')?.classList.add('hidden');
        });
    });
}

// Initialize tooltips
function initTooltips() {
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        const tooltipText = element.getAttribute('data-tooltip');
        
        element.addEventListener('mouseenter', () => {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip absolute z-50 px-2 py-1 text-sm bg-gray-900 text-white rounded shadow-lg';
            tooltip.textContent = tooltipText;
            tooltip.style.top = `${element.offsetTop - 30}px`;
            tooltip.style.left = `${element.offsetLeft}px`;
            tooltip.id = 'active-tooltip';
            document.body.appendChild(tooltip);
        });
        
        element.addEventListener('mouseleave', () => {
            document.getElementById('active-tooltip')?.remove();
        });
    });
}

// Table search functionality
function initTableSearch() {
    document.querySelectorAll('[data-table-search]').forEach(input => {
        const tableId = input.getAttribute('data-table-search');
        const table = document.getElementById(tableId);
        
        if (table) {
            input.addEventListener('input', (e) => {
                const searchTerm = e.target.value.toLowerCase();
                table.querySelectorAll('tbody tr').forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(searchTerm) ? '' : 'none';
                });
            });
        }
    });
}

// Export to CSV
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    const csv = [];
    
    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = [];
        cols.forEach(col => {
            rowData.push(`"${col.textContent.replace(/"/g, '""')}"`);
        });
        csv.push(rowData.join(','));
    });
    
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${filename}.csv`;
    link.click();
}

// Print functionality
function printElement(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
        <head>
            <title>Print</title>
            <link rel="stylesheet" href="/static/css/styles.css">
            <script src="https://cdn.tailwindcss.com"><\/script>
        </head>
        <body class="p-8">
            ${element.innerHTML}
        </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    initDropdowns();
    initModals();
    initTooltips();
    initTableSearch();
    
    console.log('Booklet ERP initialized');
});

// Handle HTMX after swap
document.body.addEventListener('htmx:afterSwap', function(event) {
    // Re-initialize components after HTMX swap
    initDropdowns();
    initModals();
});

// Handle HTMX errors
document.body.addEventListener('htmx:responseError', function(event) {
    const response = event.detail.xhr;
    if (response.status === 401) {
        window.location.href = '/auth/login';
    } else if (response.status === 403) {
        showToast('You do not have permission to perform this action', 'error');
    } else if (response.status >= 500) {
        showToast('A server error occurred. Please try again.', 'error');
    }
});
