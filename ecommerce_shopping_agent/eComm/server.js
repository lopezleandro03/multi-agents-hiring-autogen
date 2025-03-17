const express = require('express');
const path = require('path');
const fs = require('fs');
const swaggerUi = require('swagger-ui-express');
const YAML = require('yamljs');
const app = express();

// Load Swagger document
const swaggerDocument = YAML.load(path.join(__dirname, 'api.yaml'));

// Add JSON middleware
app.use(express.json());

// Serve API documentation
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerDocument));

// Serve static files
app.use(express.static(path.join(__dirname)));

// Load mock data
const productsData = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'products.json'), 'utf8'));
const ordersData = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'orders.json'), 'utf8'));

// API endpoints
app.get('/api/products', (req, res) => {
    res.json(productsData.products);
});

app.get('/api/orders/:orderId', (req, res) => {
    const order = ordersData.orders.find(o => o.id === req.params.orderId);
    if (order) {
        res.json(order);
    } else {
        // Return first order as default if order ID doesn't exist
        res.json(ordersData.orders[0]);
    }
});

// Add POST endpoint for creating new orders
app.post('/api/orders', (req, res) => {
    try {
        const newOrder = req.body;
        
        // Validate required fields
        if (!newOrder.id || !newOrder.customerName || !newOrder.items) {
            return res.status(400).json({ error: 'Missing required fields: id, customerName, items' });
        }

        // Check if order ID already exists
        if (ordersData.orders.some(order => order.id === newOrder.id)) {
            return res.status(409).json({ error: 'Order ID already exists' });
        }

        // Add new order to the orders array
        ordersData.orders.push(newOrder);

        // Save updated orders to file
        fs.writeFileSync(
            path.join(__dirname, 'data', 'orders.json'),
            JSON.stringify(ordersData, null, 2)
        );

        res.status(201).json(newOrder);
    } catch (error) {
        res.status(500).json({ error: 'Failed to create order' });
    }
});

// HTML routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('/faq', (req, res) => {
    res.sendFile(path.join(__dirname, 'faq.html'));
});

// Handle 404
app.use((req, res) => {
    res.status(404).send('Page not found');
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
    console.log(`Server running on port ${port}`);
    console.log(`API documentation available at http://localhost:${port}/api-docs`);
});