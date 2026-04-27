# Web Frontend Perspectives

domain: web-frontend

## Perspective 1: Frontend Architect
Asks: Is this architecture scalable and maintainable?
- Component architecture and composition patterns
- State management approach (Redux, Zustand, Context, signals)
- Routing strategy and code splitting / lazy loading
- Design system or component library usage and consistency
- SSR vs CSR decisions and hydration strategy
- Build toolchain and bundler configuration (Vite, webpack, turbopack)
- TypeScript coverage and type safety boundaries
- API layer abstraction (fetch wrappers, generated clients, tanstack-query)

## Perspective 2: Accessibility & UX Engineer
Asks: Can everyone use this application effectively?
- WCAG compliance level and known gaps
- Keyboard navigation across all interactive elements
- Screen reader support and ARIA attribute usage
- Color contrast ratios and visual accessibility
- Focus management on route changes and modal dialogs
- Error state communication (form validation, network errors)
- Loading state patterns (skeleton screens, spinners, progressive)
- Responsive breakpoints and mobile experience quality
- Internationalization and localization readiness

## Perspective 3: Performance Engineer
Asks: How fast is this for real users on real networks?
- Core Web Vitals (LCP, INP, CLS) measurement and budgets
- Bundle size budget and tree-shaking effectiveness
- Image optimization (formats, lazy loading, responsive images)
- Caching strategy (service worker, CDN, HTTP cache headers)
- Third-party script impact on load time and main thread
- Prefetching and preloading strategy for navigation
- Render-blocking resources and critical CSS extraction
- Memory leak detection (component cleanup, event listeners)
