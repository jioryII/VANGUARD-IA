/*
██╗   ██╗ █████╗ ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ 
██║   ██║██╔══██╗████╗  ██║██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
██║   ██║███████║██╔██╗ ██║██║  ███╗██║   ██║███████║██████╔╝██║  ██║
╚██╗ ██╔╝██╔══██║██║╚██╗██║██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
 ╚████╔╝ ██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
  ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 

                              ██╗ █████╗ 
                              ██║██╔══██╗
                              ██║███████║
                              ██║██╔══██║
                              ██║██║  ██║
                              ╚═╝╚═╝  ╚═╝
*/

document.addEventListener('DOMContentLoaded', () => {
    const headerElement = document.querySelector('.main-header');

    const scrollLinks = document.querySelectorAll('a.scroll-to[href^="#"], .glassmorphic-nav ul li a[href^="#"]');
    scrollLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                let headerOffset = 0;
                if (headerElement && getComputedStyle(headerElement).position === 'fixed') {
                    headerOffset = headerElement.offsetHeight + 15;
                }
                
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({ top: offsetPosition, behavior: 'smooth' });
            }
        });
    });

    const sections = document.querySelectorAll('main section[id]');
    const navAnchors = document.querySelectorAll('.glassmorphic-nav ul li a');

    function changeNavActiveState() {
        let currentSectionId = '';
        const headerHeight = headerElement ? headerElement.offsetHeight : 0;

        sections.forEach(section => {
            const sectionTop = section.offsetTop - headerHeight - Math.min(100, window.innerHeight * 0.2);
            if (window.pageYOffset >= sectionTop) {
                currentSectionId = section.getAttribute('id');
            }
        });

        navAnchors.forEach(a => {
            a.classList.remove('active');
            if (a.getAttribute('href').substring(1) === currentSectionId) {
                a.classList.add('active');
            }
        });
        
        if (!currentSectionId && sections.length > 0 && window.pageYOffset < sections[0].offsetTop - headerHeight - 100) {
            const homeLink = document.querySelector('.glassmorphic-nav ul li a[href="#inicio"]');
            if (homeLink) homeLink.classList.add('active');
        }
    }
    window.addEventListener('scroll', changeNavActiveState);
    changeNavActiveState(); 

    const animatedElements = document.querySelectorAll('.feature-card, .sector-card, .screenshots-grid img, .platform-image-container');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {

                entry.target.style.animation = `fadeInSlideUp 0.7s ease-out forwards 0.1s`;
                 observer.unobserve(entry.target); 
            }
        });
    }, { threshold: 0.1 });

    animatedElements.forEach(el => {
        el.style.opacity = '0'; 
        observer.observe(el);
    });
});