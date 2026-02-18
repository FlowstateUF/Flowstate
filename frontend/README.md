# Flowstate Frontend

This is the React frontend for Flowstate, built with Vite.

## Requirements
- Node.js 22 LTS (or 18/20 LTS also acceptable)
- npm (comes with Node)

*** Simply run 'npm install' and it will install the dependencies below
    - react-router-dom (run 'npm install react-router-dom' in the frontend terminal)
    - install mantine using 'npm install @mantine/core @mantine/hooks @mantine/form @mantine/notifications' in the frontend folder
    - npm install @tabler/icons-react

## Guide
- On first ever use (after cloning the repo), run 'npm install' in the terminal within the frontend folder
- To start the app, run 'npm run dev' in the frontend folder terminal and click the provided link to open the app

# Development
**Adding a new page:**
1. Create file in `src/pages/YourPage.jsx`
2. Create corresponding CSS in `src/components/YourPage/YourPage.css` (optional)
3. Add route in `main.jsx`:
4. Link to it: `<button onClick={() => navigate('/your-page')}>Go</button>`

**Adding a reusable component:**
1. Create file in `src/components/ComponentName.jsx`
2. Export it: `export default ComponentName`
3. Import where needed: `import ComponentName from '../components/ComponentName.jsx'`
4. Use it: `<ComponentName prop1="value" />`

**Adding styles:**
- **Page-specific styles** → `src/components/PageName/PageName.css`
- **Shared styles** → Keep in `App.css` or create `global.css`