document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('propertySearchForm');
    const resultsDiv = document.getElementById('propertyResults');
    const loadingSpinner = document.getElementById('loadingSpinner');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Show loading spinner
        loadingSpinner.classList.remove('d-none');
        resultsDiv.innerHTML = '';
        
        // Get form values
        const zipCode = document.getElementById('zipCode').value;
        const maxBudget = document.getElementById('maxBudget').value;
        const minSqft = document.getElementById('minSqft').value;
        const maxSqft = document.getElementById('maxSqft').value;

        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    zip_code: zipCode,
                    max_budget: maxBudget,
                    min_sqft: minSqft,
                    max_sqft: maxSqft
                }),
            });

            const properties = await response.json();
            
            // Hide loading spinner
            loadingSpinner.classList.add('d-none');
            
            // Display results
            if (properties.length === 0) {
                resultsDiv.innerHTML = `
                    <div class="col-12 text-center">
                        <div class="alert alert-info" role="alert">
                            <i class="fas fa-info-circle me-2"></i>
                            No properties found matching your criteria. Try adjusting your filters.
                        </div>
                    </div>
                `;
                return;
            }

            properties.forEach(property => {
                const propertyCard = document.createElement('div');
                propertyCard.className = 'col-md-6 col-lg-4';
                propertyCard.innerHTML = `
                    <div class="property-card">
                        <img src="${property.image}" alt="${property.address}" class="property-image">
                        <div class="property-details">
                            <div class="property-price">${property.price}</div>
                            <div class="property-address">${property.address}</div>
                            <div class="property-features">
                                <div class="feature-item">
                                    <i class="fas fa-bed"></i>
                                    <span>${property.beds} Beds</span>
                                </div>
                                <div class="feature-item">
                                    <i class="fas fa-bath"></i>
                                    <span>${property.baths} Baths</span>
                                </div>
                                <div class="feature-item">
                                    <i class="fas fa-ruler-combined"></i>
                                    <span>${property.sqft}</span>
                                </div>
                            </div>
                            <div class="text-center mt-3">
                                <a href="${property.link}" target="_blank" class="view-property-btn">
                                    <i class="fas fa-external-link-alt me-2"></i>View Property
                                </a>
                            </div>
                        </div>
                    </div>
                `;
                resultsDiv.appendChild(propertyCard);
            });

        } catch (error) {
            console.error('Error:', error);
            loadingSpinner.classList.add('d-none');
            resultsDiv.innerHTML = `
                <div class="col-12 text-center">
                    <div class="alert alert-danger" role="alert">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        Error fetching properties. Please try again later.
                    </div>
                </div>
            `;
        }
    });
});
