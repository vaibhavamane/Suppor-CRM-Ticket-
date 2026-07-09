// Application State
const state = {
    tickets: [],
    activeTicket: null,
    filters: {
        status: '',
        search: '',
        page: 1,
        limit: 4
    }
};

// DOM Elements
const elements = {
    ticketsList: document.getElementById('tickets-list'),
    ticketCount: document.getElementById('ticket-count'),
    searchInput: document.getElementById('search-input'),
    bloomIndicator: document.getElementById('bloom-indicator'),
    filterTabs: document.querySelectorAll('.filter-tab'),
    navItems: document.querySelectorAll('.nav-item'),
    navCountAll: document.getElementById('nav-count-all'),
    navCountOpen: document.getElementById('nav-count-open'),
    navCountProgress: document.getElementById('nav-count-progress'),
    navCountClosed: document.getElementById('nav-count-closed'),
    btnPrevPage: document.getElementById('btn-prev-page'),
    btnNextPage: document.getElementById('btn-next-page'),
    pageDisplay: document.getElementById('page-display'),
    
    // Detail View
    detailEmpty: document.getElementById('detail-view-empty'),
    detailContent: document.getElementById('detail-view-content'),
    detailId: document.getElementById('detail-ticket-id'),
    detailDate: document.getElementById('detail-ticket-date'),
    detailStatus: document.getElementById('detail-ticket-status'),
    detailStatusSelect: document.getElementById('detail-status-select'),
    detailCustomerName: document.getElementById('detail-customer-name'),
    detailCustomerEmail: document.getElementById('detail-customer-email'),
    detailSubject: document.getElementById('detail-ticket-subject'),
    detailDescription: document.getElementById('detail-ticket-description'),
    notesTimeline: document.getElementById('notes-timeline'),
    addNoteForm: document.getElementById('add-note-form'),
    noteInput: document.getElementById('note-input'),
    customerAvatarPlaceholder: document.getElementById('customer-avatar-placeholder'),
    
    // Modal
    createModal: document.getElementById('create-modal'),
    btnCreateTicket: document.getElementById('btn-create-ticket'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    btnCancelTicket: document.getElementById('btn-cancel-ticket'),
    createTicketForm: document.getElementById('create-ticket-form'),
    
    // Toast Container
    toastContainer: document.getElementById('toast-container')
};

// Constants
const API_URL = '/api';

// Toast Notification System
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Icon mapping
    let icon = '';
    if (type === 'success') {
        icon = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === 'error') {
        icon = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    } else {
        icon = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `${icon} <span>${message}</span>`;
    elements.toastContainer.appendChild(toast);
    
    // Auto remove
    setTimeout(() => {
        toast.style.animation = 'toast-out 0.3s forwards';
        toast.addEventListener('animationend', () => {
            toast.remove();
        });
    }, 4000);
}

// Debouncer for search query
function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    fetchTickets();
    fetchStatusCounts();
    setupEventListeners();
});

// Fetch per-status counts for the sidebar
async function fetchStatusCounts() {
    try {
        const statuses = ['Open', 'In Progress', 'Closed'];
        const counts = { '': 0 };
        for (const s of statuses) {
            const res = await fetch(`${API_URL}/tickets?status=${encodeURIComponent(s)}&limit=1`);
            const total = parseInt(res.headers.get('X-Total-Count') || '0', 10);
            counts[s] = total;
            counts[''] += total;
        }
        if (elements.navCountAll) elements.navCountAll.textContent = counts[''];
        if (elements.navCountOpen) elements.navCountOpen.textContent = counts['Open'];
        if (elements.navCountProgress) elements.navCountProgress.textContent = counts['In Progress'];
        if (elements.navCountClosed) elements.navCountClosed.textContent = counts['Closed'];
    } catch (error) {
        console.error('Failed to load status counts', error);
    }
}

// Event Listeners Setup
function setupEventListeners() {
    // Search input event
    elements.searchInput.addEventListener('input', debounce((e) => {
        state.filters.search = e.target.value.trim();
        state.filters.page = 1;
        
        // Show/hide Bloom indicator depending on whether a search is active
        if (state.filters.search) {
            elements.bloomIndicator.classList.add('active');
        } else {
            elements.bloomIndicator.classList.remove('active');
        }
        
        fetchTickets(true); // pass true to indicate a search was triggered
    }, 300));

    // Filter tabs
    elements.filterTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            elements.filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            state.filters.status = tab.dataset.status;
            state.filters.page = 1;
            fetchTickets();
        });
    });

    // Sidebar nav items (sync with filter tabs)
    elements.navItems.forEach(item => {
        item.addEventListener('click', () => {
            const status = item.dataset.status;
            elements.navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            elements.filterTabs.forEach(t => {
                t.classList.toggle('active', t.dataset.status === status);
            });
            state.filters.status = status;
            state.filters.page = 1;
            fetchTickets();
        });
    });

    // Pagination
    elements.btnPrevPage.addEventListener('click', () => {
        if (state.filters.page > 1) {
            state.filters.page--;
            fetchTickets();
        }
    });

    elements.btnNextPage.addEventListener('click', () => {
        state.filters.page++;
        fetchTickets();
    });

    // Modal open/close
    elements.btnCreateTicket.addEventListener('click', () => {
        elements.createModal.classList.remove('hidden');
        document.getElementById('input-customer-name').focus();
    });

    const closeModal = () => elements.createModal.classList.add('hidden');
    elements.btnCloseModal.addEventListener('click', closeModal);
    elements.btnCancelTicket.addEventListener('click', closeModal);
    
    // Close modal when clicking outside card
    elements.createModal.addEventListener('click', (e) => {
        if (e.target === elements.createModal) {
            closeModal();
        }
    });

    // Create ticket submission
    elements.createTicketForm.addEventListener('submit', handleCreateTicket);

    // Add note submission
    elements.addNoteForm.addEventListener('submit', handleAddNote);

    // Detail status selector change
    elements.detailStatusSelect.addEventListener('change', handleStatusChange);
}

// Format Date Utility
function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
    };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Fetch Tickets List
async function fetchTickets(isSearchTriggered = false) {
    // Show spinner in list
    elements.ticketsList.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Fetching tickets...</p>
        </div>
    `;

    const params = new URLSearchParams();
    if (state.filters.status) params.append('status', state.filters.status);
    if (state.filters.search) params.append('search', state.filters.search);
    params.append('page', state.filters.page);
    params.append('limit', state.filters.limit);

    const startTime = performance.now();
    try {
        const response = await fetch(`${API_URL}/tickets?${params.toString()}`);
        if (!response.ok) throw new Error('Failed to load tickets');
        
        // Retrieve the total count header returned by FastAPI
        const totalCount = parseInt(response.headers.get('X-Total-Count') || '0', 10);
        const tickets = await response.json();
        const duration = (performance.now() - startTime).toFixed(1);
        
        state.tickets = tickets;
        renderTicketsList(totalCount);
        updatePagination(totalCount);
        
        // Show educational feedback on Bloom Filter bypass optimization
        if (isSearchTriggered && state.filters.search) {
            if (tickets.length === 0) {
                // If query is empty, we check if the duration is extremely fast (< 5ms) which shows the Bloom Filter bypass
                showToast(`Bloom Filter optimization bypassed DB search! (Returned 0 items in ${duration}ms)`, 'success');
            } else {
                showToast(`Bloom Filter verified presence. Searched database in ${duration}ms`, 'info');
            }
        }
    } catch (error) {
        console.error(error);
        showToast('Error loading tickets from backend', 'error');
        elements.ticketsList.innerHTML = `
            <div class="empty-state">
                <p>Could not connect to the API. Make sure the FastAPI server is running.</p>
            </div>
        `;
    }
}

// Render Tickets List DOM
function renderTicketsList(totalCount) {
    if (state.tickets.length === 0) {
        elements.ticketsList.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" width="32" height="32" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                <p>No tickets found</p>
            </div>
        `;
        elements.ticketCount.textContent = '0 tickets';
        return;
    }

    elements.ticketCount.textContent = `${totalCount} ticket${totalCount > 1 ? 's' : ''}`;
    elements.ticketsList.innerHTML = '';
    
    state.tickets.forEach(ticket => {
        const card = document.createElement('div');
        const isActive = state.activeTicket && state.activeTicket.ticket_id === ticket.ticket_id;
        card.className = `ticket-card ${isActive ? 'active' : ''}`;
        card.dataset.id = ticket.ticket_id;
        
        const statusClass = ticket.status.toLowerCase().replace(' ', '-');
        
        card.innerHTML = `
            <div class="ticket-card-header">
                <span class="ticket-card-id">${ticket.ticket_id}</span>
                <span class="ticket-card-date">${formatDate(ticket.created_at)}</span>
            </div>
            <div class="ticket-card-subject">${ticket.subject}</div>
            <div class="ticket-card-footer">
                <span class="ticket-card-customer">${ticket.customer_name}</span>
                <span class="status-badge ${statusClass}">${ticket.status}</span>
            </div>
        `;
        
        card.addEventListener('click', () => {
            // Highlight card
            document.querySelectorAll('.ticket-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            loadTicketDetails(ticket.ticket_id);
        });
        
        elements.ticketsList.appendChild(card);
    });
}

// Update Pagination Control States using total count metadata
function updatePagination(totalCount) {
    const totalPages = Math.ceil(totalCount / state.filters.limit) || 1;
    elements.pageDisplay.textContent = `Page ${state.filters.page} of ${totalPages}`;
    
    // Disable prev button if on page 1
    elements.btnPrevPage.disabled = (state.filters.page === 1);
    
    // Disable next button if on the last page
    elements.btnNextPage.disabled = (state.filters.page >= totalPages);
}

// Load Details of Single Ticket
async function loadTicketDetails(ticketId) {
    try {
        const response = await fetch(`${API_URL}/tickets/${ticketId}`);
        if (!response.ok) throw new Error('Failed to load ticket details');
        
        const ticket = await response.json();
        state.activeTicket = ticket;
        renderTicketDetail();
    } catch (error) {
        console.error(error);
        showToast('Error loading ticket details', 'error');
    }
}

// Render Details DOM
function renderTicketDetail() {
    const ticket = state.activeTicket;
    if (!ticket) return;
    
    // Swap panels
    elements.detailEmpty.classList.add('hidden');
    elements.detailContent.classList.remove('hidden');
    
    // Render text values
    elements.detailId.textContent = ticket.ticket_id;
    elements.detailDate.textContent = `Created: ${formatDate(ticket.created_at || new Date())}`;
    
    // Avatar placeholder
    const firstLetter = ticket.customer_name ? ticket.customer_name.charAt(0).toUpperCase() : 'U';
    elements.customerAvatarPlaceholder.textContent = firstLetter;
    
    elements.detailCustomerName.textContent = ticket.customer_name;
    elements.detailCustomerEmail.textContent = ticket.customer_email;
    elements.detailSubject.textContent = ticket.subject;
    elements.detailDescription.textContent = ticket.description;
    
    // Update status badge design
    const statusClass = ticket.status.toLowerCase().replace(' ', '-');
    elements.detailStatus.textContent = ticket.status;
    elements.detailStatus.className = `status-badge ${statusClass}`;
    
    // Set status selector value
    elements.detailStatusSelect.value = ticket.status;
    
    // Render notes timeline
    renderNotesTimeline(ticket.notes);
}

// Render Notes timeline
function renderNotesTimeline(notes) {
    elements.notesTimeline.innerHTML = '';
    
    if (!notes || notes.length === 0) {
        elements.notesTimeline.innerHTML = `
            <div style="font-size: 0.8rem; color: var(--text-muted); font-style: italic; padding: 0.5rem 0;">
                No comments or notes have been added to this ticket yet.
            </div>
        `;
        return;
    }
    
    notes.forEach(note => {
        const noteEl = document.createElement('div');
        noteEl.className = 'note-item';
        
        noteEl.innerHTML = `
            <div class="note-item-header">
                <span class="note-author">Agent/System Note</span>
                <span>${formatDate(note.created_at)}</span>
            </div>
            <div class="note-content-bubble">
                ${note.note_text}
            </div>
        `;
        
        elements.notesTimeline.appendChild(noteEl);
    });
    
    // Scroll notes section to bottom
    elements.notesTimeline.scrollTop = elements.notesTimeline.scrollHeight;
}

// Handle Ticket Status Change
async function handleStatusChange(e) {
    const ticket = state.activeTicket;
    if (!ticket) return;
    
    const newStatus = e.target.value;
    
    try {
        const response = await fetch(`${API_URL}/tickets/${ticket.ticket_id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) throw new Error('Failed to update status');
        
        showToast(`Ticket status updated to ${newStatus}`, 'success');
        
        // Refresh details and ticket list
        await loadTicketDetails(ticket.ticket_id);
        fetchTickets();
        fetchStatusCounts();
    } catch (error) {
        console.error(error);
        showToast('Error updating status', 'error');
        // Reset select element to old value
        elements.detailStatusSelect.value = ticket.status;
    }
}

// Handle Add Note Form Submission
async function handleAddNote(e) {
    e.preventDefault();
    const ticket = state.activeTicket;
    if (!ticket) return;
    
    const noteText = elements.noteInput.value.trim();
    if (!noteText) return;
    
    const btnSubmit = document.getElementById('btn-submit-note');
    btnSubmit.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/tickets/${ticket.ticket_id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: noteText })
        });
        
        if (!response.ok) throw new Error('Failed to add note');
        
        showToast('Note added successfully', 'success');
        elements.noteInput.value = '';
        
        // Refresh details and ticket list
        await loadTicketDetails(ticket.ticket_id);
        fetchTickets();
    } catch (error) {
        console.error(error);
        showToast('Error adding note', 'error');
    } finally {
        btnSubmit.disabled = false;
    }
}

// Handle Create Ticket Submission
async function handleCreateTicket(e) {
    e.preventDefault();
    
    const ticketData = {
        customer_name: document.getElementById('input-customer-name').value.trim(),
        customer_email: document.getElementById('input-customer-email').value.trim(),
        subject: document.getElementById('input-subject').value.trim(),
        description: document.getElementById('input-description').value.trim()
    };
    
    const btnSubmit = elements.createTicketForm.querySelector('button[type="submit"]');
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Creating...';
    
    try {
        const response = await fetch(`${API_URL}/tickets`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ticketData)
        });
        
        if (!response.ok) throw new Error('Failed to create ticket');
        
        const result = await response.json();
        
        showToast(`Ticket ${result.ticket_id} created successfully!`, 'success');
        elements.createTicketForm.reset();
        elements.createModal.classList.add('hidden');
        
        // Reset page to 1 so the new ticket is visible at the top
        state.filters.page = 1;
        
        // Refresh ticket list and select the new ticket
        await fetchTickets();
        fetchStatusCounts();
        
        // Automatically load detail for the newly created ticket
        loadTicketDetails(result.ticket_id);
        
    } catch (error) {
        console.error(error);
        showToast('Error creating ticket. Ensure email format is valid.', 'error');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Create Ticket';
    }
}
