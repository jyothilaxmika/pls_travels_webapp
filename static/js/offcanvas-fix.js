// Fix for offcanvas appearing stuck open
document.addEventListener('DOMContentLoaded', function() {
    const offcanvasElement = document.getElementById('sidebarMenu');
    
    if (offcanvasElement) {
        // Force offcanvas to start closed
        offcanvasElement.classList.remove('show');
        offcanvasElement.classList.remove('showing');
        offcanvasElement.style.visibility = 'hidden';
        offcanvasElement.style.transform = 'translateX(-100%)';
        offcanvasElement.style.opacity = '0';
        
        // Force close any existing Bootstrap offcanvas instance
        const existingInstance = bootstrap.Offcanvas.getInstance(offcanvasElement);
        if (existingInstance) {
            existingInstance.hide();
        }
        
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
                // Force hide on large screens
                offcanvasElement.classList.remove('show');
                offcanvasElement.classList.remove('showing');
                offcanvasElement.style.visibility = 'hidden';
                offcanvasElement.style.transform = 'translateX(-100%)';
                offcanvasElement.style.opacity = '0';
            }
        });
        
        // Monitor for any classes being added that might show the offcanvas
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    // If on desktop screen and offcanvas is trying to show, force hide it
                    if (window.innerWidth >= 1200 && offcanvasElement.classList.contains('show')) {
                        setTimeout(() => {
                            offcanvasElement.classList.remove('show');
                            offcanvasElement.classList.remove('showing');
                            offcanvasElement.style.visibility = 'hidden';
                            offcanvasElement.style.transform = 'translateX(-100%)';
                            offcanvasElement.style.opacity = '0';
                        }, 0);
                    }
                }
            });
        });
        
        observer.observe(offcanvasElement, {
            attributes: true,
            attributeFilter: ['class']
        });
    }
});