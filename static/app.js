// Socket.IO connection
const socket = io();

// Connection status
const connectionStatus = document.getElementById('connection-status');
const statusText = document.getElementById('status-text');

// Tree display elements
const treeDisplay = document.getElementById('tree-display');
const rawTreeDisplay = document.getElementById('raw-tree');

// Initialize connection status
updateConnectionStatus('connecting', 'Connecting...');

// Socket event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    updateConnectionStatus('connected', 'Connected');
    showNotification('Connected to server', 'success');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateConnectionStatus('disconnected', 'Disconnected');
    showNotification('Disconnected from server', 'error');
});

socket.on('tree_update', (data) => {
    console.log('Tree updated:', data);
    updateTreeDisplay(data.pretty || '');
    updateRawTree(data.tree || []);
    
    const event = data.event;
    if (event) {
        showNotification(`Tree updated: ${event}`, 'info');
    }
});

socket.on('operation_success', (data) => {
    console.log('Operation successful:', data);
    showNotification(`Operation ${data.operation} completed`, 'success');
});

socket.on('error', (data) => {
    console.error('Error:', data);
    showNotification(`Error: ${data.message}`, 'error');
});

// Update connection status
function updateConnectionStatus(status, text) {
    connectionStatus.className = `status ${status}`;
    statusText.textContent = text;
}

// Update tree display
function updateTreeDisplay(pretty) {
    if (pretty) {
        treeDisplay.textContent = pretty;
    } else {
        treeDisplay.innerHTML = '<div class="loading">No tree data available</div>';
    }
}

// Update raw tree data
function updateRawTree(tree) {
    rawTreeDisplay.textContent = JSON.stringify(tree, null, 2);
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Form submission
document.getElementById('apply-form').addEventListener('submit', (e) => {
    e.preventDefault();
    
    const parent = document.getElementById('parent').value.trim();
    const meta = document.getElementById('meta').value.trim();
    const child = document.getElementById('child').value.trim();
    
    if (!parent || !child) {
        showNotification('Parent and child are required', 'error');
        return;
    }
    
    socket.emit('apply', {
        parent: parent,
        meta: meta || '',
        child: child
    });
    
    // Clear form
    document.getElementById('parent').value = '';
    document.getElementById('meta').value = '';
    document.getElementById('child').value = '';
});

// Undo function
function undo() {
    socket.emit('undo', { n: 1 });
}

// Redo function
function redo() {
    socket.emit('redo', { n: 1 });
}

// Refresh tree
function refreshTree() {
    socket.emit('get_tree');
}

// Batch operations
function addBatchItem() {
    const container = document.getElementById('batch-operations');
    const item = document.createElement('div');
    item.className = 'batch-item';
    item.innerHTML = `
        <input type="text" class="batch-parent" placeholder="Parent">
        <input type="text" class="batch-meta" placeholder="Meta">
        <input type="text" class="batch-child" placeholder="Child">
        <button type="button" class="btn-remove" onclick="removeBatchItem(this)">×</button>
    `;
    container.appendChild(item);
}

function removeBatchItem(button) {
    button.parentElement.remove();
}

function applyBatch() {
    const items = document.querySelectorAll('.batch-item');
    const moves = [];
    
    items.forEach(item => {
        const parent = item.querySelector('.batch-parent').value.trim();
        const meta = item.querySelector('.batch-meta').value.trim();
        const child = item.querySelector('.batch-child').value.trim();
        
        if (parent && child) {
            moves.push({
                parent: parent,
                meta: meta || '',
                child: child
            });
        }
    });
    
    if (moves.length === 0) {
        showNotification('Please add at least one valid move', 'error');
        return;
    }
    
    socket.emit('apply_batch', { moves: moves });
    
    // Clear batch inputs
    items.forEach(item => {
        item.querySelector('.batch-parent').value = '';
        item.querySelector('.batch-meta').value = '';
        item.querySelector('.batch-child').value = '';
    });
}

// Request initial tree on load
socket.on('connect', () => {
    setTimeout(() => {
        socket.emit('get_tree');
    }, 500);
});
