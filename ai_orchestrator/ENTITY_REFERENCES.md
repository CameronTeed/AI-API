# Entity References for Clickable Keywords

## Overview

The AI orchestrator now includes **entity references** in all date idea responses, enabling users to click on keywords in the AI responses to navigate to full database entries.

## How It Works

### 1. Vector Store Enhancement
Each date idea now includes:
- `entity_references`: Object containing clickable database references
- `primary_entity`: The main date idea entity
- `related_entities`: Array of related entities (venues, cities, categories, etc.)

### 2. Entity Types
The system supports these clickable entity types:

| Type | Description | Example URL |
|------|-------------|-------------|
| `date_idea` | Main date activity | `/api/date-ideas/date_idea_001` |
| `venue` | Physical location | `/api/venues/venue_met_museum_001` |
| `city` | Geographic location | `/api/cities/new_york` |
| `category` | Activity category | `/api/categories/romantic` |
| `price_tier` | Budget level | `/api/price-tiers/2` |
| `business` | Business/establishment | `/api/businesses/business_met_001` |

### 3. Response Structure

```json
{
  "summary": "Here are some romantic date ideas...",
  "options": [
    {
      "title": "Art Museum Visit",
      "categories": ["cultural", "art", "indoor"],
      "price": "$$",
      "duration_min": 180,
      "why_it_fits": "Perfect for culture enthusiasts...",
      "logistics": "Visit the Metropolitan Museum...",
      "website": "https://metmuseum.org",
      "source": "vector_store",
      "entity_references": {
        "primary_entity": {
          "id": "date_idea_002",
          "type": "date_idea",
          "title": "Art Museum Visit",
          "url": "/api/date-ideas/date_idea_002"
        },
        "related_entities": [
          {
            "id": "venue_met_museum_001",
            "type": "venue",
            "title": "Metropolitan Museum of Art",
            "url": "/api/venues/venue_met_museum_001"
          },
          {
            "id": "new_york",
            "type": "city",
            "title": "New York",
            "url": "/api/cities/new_york"
          },
          {
            "id": "cultural",
            "type": "category",
            "title": "cultural",
            "url": "/api/categories/cultural"
          },
          {
            "id": "price_tier_2",
            "type": "price_tier",
            "title": "$$",
            "url": "/api/price-tiers/2"
          }
        ]
      }
    }
  ]
}
```

## Frontend Implementation

### 1. Rendering Clickable Keywords

When displaying AI responses, scan for entity references and make them clickable:

```javascript
function renderClickableText(text, entityReferences) {
  let clickableText = text;
  
  // Replace entity titles with clickable links
  entityReferences.related_entities.forEach(entity => {
    const regex = new RegExp(`\\b${entity.title}\\b`, 'gi');
    clickableText = clickableText.replace(regex, 
      `<a href="${entity.url}" class="entity-link" data-type="${entity.type}">
        ${entity.title}
      </a>`
    );
  });
  
  return clickableText;
}
```

### 2. Entity Link Styling

```css
.entity-link {
  color: #007bff;
  text-decoration: underline;
  cursor: pointer;
  font-weight: 500;
}

.entity-link[data-type="venue"] {
  color: #28a745; /* Green for venues */
}

.entity-link[data-type="city"] {
  color: #6f42c1; /* Purple for cities */
}

.entity-link[data-type="category"] {
  color: #fd7e14; /* Orange for categories */
}

.entity-link[data-type="price_tier"] {
  color: #20c997; /* Teal for price tiers */
}
```

### 3. Click Handlers

```javascript
function handleEntityClick(entityId, entityType, entityUrl) {
  // Route to the appropriate page/component
  switch(entityType) {
    case 'date_idea':
      router.push(`/date-ideas/${entityId}`);
      break;
    case 'venue':
      router.push(`/venues/${entityId}`);
      break;
    case 'city':
      router.push(`/cities/${entityId}`);
      break;
    case 'category':
      router.push(`/categories/${entityId}`);
      break;
    case 'business':
      router.push(`/businesses/${entityId}`);
      break;
    default:
      window.open(entityUrl, '_blank');
  }
}
```

### 4. Entity Tooltips

Add hover tooltips for better UX:

```javascript
function addEntityTooltips() {
  document.querySelectorAll('.entity-link').forEach(link => {
    link.addEventListener('mouseenter', async (e) => {
      const entityType = e.target.dataset.type;
      const entityId = e.target.href.split('/').pop();
      
      // Fetch entity preview data
      const preview = await fetchEntityPreview(entityType, entityId);
      showTooltip(e.target, preview);
    });
  });
}
```

## API Endpoints

Your backend should implement these endpoints to serve entity data:

```
GET /api/date-ideas/{id}      - Full date idea details
GET /api/venues/{id}          - Venue information
GET /api/cities/{id}          - City information and other activities
GET /api/categories/{id}      - Category with related date ideas
GET /api/price-tiers/{tier}   - Price tier information
GET /api/businesses/{id}      - Business details
```

## Benefits

1. **Enhanced Navigation**: Users can explore related content naturally
2. **Better Discovery**: Clicking on cities shows other activities there
3. **Contextual Exploration**: Categories lead to similar date ideas
4. **Rich Metadata**: Each entity carries database references
5. **SEO Friendly**: Structured data improves search indexing

## Example User Flow

1. User asks: "I want a romantic date in New York"
2. AI responds with museum suggestion
3. User clicks on "New York" → sees all NYC date ideas
4. User clicks on "romantic" category → sees all romantic activities
5. User clicks on venue name → gets venue details, hours, booking

## Testing

Run the entity references test:
```bash
python3 test_entity_references.py
```

This verifies that all entity references are properly generated and serializable.
