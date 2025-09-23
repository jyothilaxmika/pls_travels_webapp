// Fix for offcanvas appearing stuck open
document.addEventListener('DOMContentLoaded', function() {
    const offcanvasElement = document.getElementById('sidebarMenu');
    
    if (offcanvasElement) {
        // Ensure offcanvas starts closed
        offcanvasElement.classList.remove('show');
        
        // Add event listeners to handle proper closing
        offcanvasElement.addEventListener('click', function(e) {
            // Close offcanvas when clicking on nav links (not dropdowns)
            if (e.target.closest('a') && !e.target.closest('.dropdown-toggle')) {
                const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasElement);
                if (bsOffcanvas) {
                    bsOffcanvas.hide();
                }
            }
        });
        
        // Close offcanvas when screen becomes large enough
        window.addEventListener('resize', function() {
            if (window.innerWidth >= 1200) {
                const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasElement);
                if (bsOffcanvas) {
                    bsOffcanvas.hide();
                }
            }
        });
    }
});