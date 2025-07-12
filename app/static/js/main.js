lucide.createIcons();
        
        // Add number counting animation
        const counters = document.querySelectorAll('.number-counter');
        counters.forEach(counter => {
            const target = parseInt(counter.textContent);
            let current = 0;
            const increment = target / 50;
            
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }
                counter.textContent = Math.floor(current);
            }, 30);
        });

document.querySelectorAll('.group').forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-2px)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
            });
        });
        
        // Add ripple effect on click
        document.querySelectorAll('.group').forEach(card => {
            card.addEventListener('click', (e) => {
                const ripple = document.createElement('div');
                ripple.className = 'absolute inset-0 rounded-xl bg-white/10 pointer-events-none';
                ripple.style.animation = 'ripple 0.6s ease-out';
                card.querySelector('.relative').appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });