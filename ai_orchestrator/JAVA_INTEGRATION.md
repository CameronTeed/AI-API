# Java Backend Integration Guide

## Overview

Your Java backend can connect to the AI orchestrator using gRPC or HTTP REST API. This guide shows both approaches with complete examples.

## Option 1: Java gRPC Client (Recommended)

### 1. Add Dependencies

Add these to your `pom.xml` (Maven) or `build.gradle` (Gradle):

#### Maven (pom.xml)
```xml
<dependencies>
    <!-- gRPC dependencies -->
    <dependency>
        <groupId>io.grpc</groupId>
        <artifactId>grpc-netty-shaded</artifactId>
        <version>1.58.0</version>
    </dependency>
    <dependency>
        <groupId>io.grpc</groupId>
        <artifactId>grpc-protobuf</artifactId>
        <version>1.58.0</version>
    </dependency>
    <dependency>
        <groupId>io.grpc</groupId>
        <artifactId>grpc-stub</artifactId>
        <version>1.58.0</version>
    </dependency>
    
    <!-- Protobuf -->
    <dependency>
        <groupId>com.google.protobuf</groupId>
        <artifactId>protobuf-java</artifactId>
        <version>3.24.4</version>
    </dependency>
    
    <!-- JSON processing -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
        <version>2.15.2</version>
    </dependency>
</dependencies>

<build>
    <extensions>
        <extension>
            <groupId>kr.motd.maven</groupId>
            <artifactId>os-maven-plugin</artifactId>
            <version>1.7.0</version>
        </extension>
    </extensions>
    <plugins>
        <plugin>
            <groupId>org.xolstice.maven.plugins</groupId>
            <artifactId>protobuf-maven-plugin</artifactId>
            <version>0.6.1</version>
            <configuration>
                <protocArtifact>com.google.protobuf:protoc:3.24.4:exe:${os.detected.classifier}</protocArtifact>
                <pluginId>grpc-java</pluginId>
                <pluginArtifact>io.grpc:protoc-gen-grpc-java:1.58.0:exe:${os.detected.classifier}</pluginArtifact>
            </configuration>
            <executions>
                <execution>
                    <goals>
                        <goal>compile</goal>
                        <goal>compile-custom</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

#### Gradle (build.gradle)
```gradle
plugins {
    id 'com.google.protobuf' version '0.9.4'
}

dependencies {
    implementation 'io.grpc:grpc-netty-shaded:1.58.0'
    implementation 'io.grpc:grpc-protobuf:1.58.0'
    implementation 'io.grpc:grpc-stub:1.58.0'
    implementation 'com.google.protobuf:protobuf-java:3.24.4'
    implementation 'com.fasterxml.jackson.core:jackson-databind:2.15.2'
    
    compileOnly 'org.apache.tomcat:annotations-api:6.0.53'
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:3.24.4"
    }
    plugins {
        grpc {
            artifact = 'io.grpc:protoc-gen-grpc-java:1.58.0'
        }
    }
    generateProtoTasks {
        all()*.plugins {
            grpc {}
        }
    }
}
```

### 2. Copy Proto File

Copy the `chat_service.proto` file to your Java project:

```bash
# Create proto directory in your Java project
mkdir -p src/main/proto

# Copy the proto file
cp /path/to/ai_orchestrator/protos/chat_service.proto src/main/proto/
```

### 3. Generate Java Classes

```bash
# Maven
mvn compile

# Gradle  
./gradlew generateProto
```

### 4. Java Client Implementation

#### AI Orchestrator Service Class

```java
package com.yourcompany.service;

import com.yourcompany.proto.AiOrchestratorGrpc;
import com.yourcompany.proto.ChatServiceProto.*;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.stub.StreamObserver;
import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

@Service
public class AiOrchestratorService {
    
    private static final Logger logger = LoggerFactory.getLogger(AiOrchestratorService.class);
    
    private final ManagedChannel channel;
    private final AiOrchestratorGrpc.AiOrchestratorStub asyncStub;
    
    public AiOrchestratorService() {
        // Connect to AI orchestrator service
        this.channel = ManagedChannelBuilder.forAddress("localhost", 50051)
                .usePlaintext()
                .build();
        this.asyncStub = AiOrchestratorGrpc.newStub(channel);
    }
    
    /**
     * Get date ideas from AI orchestrator
     */
    public CompletableFuture<DateIdeaResponse> getDateIdeas(DateIdeaRequest request) {
        CompletableFuture<DateIdeaResponse> future = new CompletableFuture<>();
        
        // Convert request to gRPC format
        ChatRequest.Builder chatRequestBuilder = ChatRequest.newBuilder()
                .addMessages(ChatMessage.newBuilder()
                        .setRole("user")
                        .setContent(request.getQuery())
                        .build())
                .setStream(true);
        
        // Add constraints if provided
        if (request.getConstraints() != null) {
            Constraints.Builder constraintsBuilder = Constraints.newBuilder();
            
            if (request.getConstraints().getCity() != null) {
                constraintsBuilder.setCity(request.getConstraints().getCity());
            }
            if (request.getConstraints().getBudgetTier() != null) {
                constraintsBuilder.setBudgetTier(request.getConstraints().getBudgetTier());
            }
            if (request.getConstraints().getIndoor() != null) {
                constraintsBuilder.setIndoor(request.getConstraints().getIndoor());
            }
            if (request.getConstraints().getCategories() != null) {
                constraintsBuilder.addAllCategories(request.getConstraints().getCategories());
            }
            
            chatRequestBuilder.setConstraints(constraintsBuilder.build());
        }
        
        // Add user location if provided
        if (request.getUserLocation() != null) {
            chatRequestBuilder.setUserLocation(UserLocation.newBuilder()
                    .setLat(request.getUserLocation().getLat())
                    .setLon(request.getUserLocation().getLon())
                    .build());
        }
        
        ChatRequest chatRequest = chatRequestBuilder.build();
        
        // Create request stream
        StreamObserver<ChatRequest> requestObserver = asyncStub.chat(new StreamObserver<ChatDelta>() {
            private StringBuilder fullText = new StringBuilder();
            private StructuredAnswer structuredAnswer = null;
            
            @Override
            public void onNext(ChatDelta chatDelta) {
                if (!chatDelta.getTextDelta().isEmpty()) {
                    fullText.append(chatDelta.getTextDelta());
                }
                
                if (chatDelta.hasStructured()) {
                    structuredAnswer = chatDelta.getStructured();
                }
                
                if (chatDelta.getDone()) {
                    // Convert to response format
                    DateIdeaResponse response = convertToDateIdeaResponse(fullText.toString(), structuredAnswer);
                    future.complete(response);
                }
            }
            
            @Override
            public void onError(Throwable throwable) {
                logger.error("Error in AI orchestrator call", throwable);
                future.completeExceptionally(throwable);
            }
            
            @Override
            public void onCompleted() {
                // Response already completed in onNext when done=true
            }
        });
        
        // Send the request
        requestObserver.onNext(chatRequest);
        requestObserver.onCompleted();
        
        return future;
    }
    
    private DateIdeaResponse convertToDateIdeaResponse(String fullText, StructuredAnswer structuredAnswer) {
        DateIdeaResponse.Builder responseBuilder = DateIdeaResponse.builder()
                .text(fullText);
        
        if (structuredAnswer != null) {
            responseBuilder.summary(structuredAnswer.getSummary());
            
            List<DateOption> options = structuredAnswer.getOptionsList().stream()
                    .map(this::convertToDateOption)
                    .toList();
            
            responseBuilder.options(options);
        }
        
        return responseBuilder.build();
    }
    
    private DateOption convertToDateOption(Option grpcOption) {
        DateOption.Builder optionBuilder = DateOption.builder()
                .title(grpcOption.getTitle())
                .categories(grpcOption.getCategoriesList())
                .price(grpcOption.getPrice())
                .durationMin(grpcOption.getDurationMin())
                .whyItFits(grpcOption.getWhyItFits())
                .logistics(grpcOption.getLogistics())
                .website(grpcOption.getWebsite())
                .source(grpcOption.getSource());
        
        // Convert entity references
        if (grpcOption.hasEntityReferences()) {
            EntityReferences entityRefs = grpcOption.getEntityReferences();
            
            // Primary entity
            com.yourcompany.model.EntityReference primaryEntity = 
                    convertEntityReference(entityRefs.getPrimaryEntity());
            optionBuilder.primaryEntity(primaryEntity);
            
            // Related entities
            List<com.yourcompany.model.EntityReference> relatedEntities = 
                    entityRefs.getRelatedEntitiesList().stream()
                            .map(this::convertEntityReference)
                            .toList();
            optionBuilder.relatedEntities(relatedEntities);
        }
        
        return optionBuilder.build();
    }
    
    private com.yourcompany.model.EntityReference convertEntityReference(EntityReference grpcEntity) {
        return com.yourcompany.model.EntityReference.builder()
                .id(grpcEntity.getId())
                .type(grpcEntity.getType())
                .title(grpcEntity.getTitle())
                .url(grpcEntity.getUrl())
                .build();
    }
    
    public void shutdown() throws InterruptedException {
        channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
    }
}
```

#### Request/Response DTOs

```java
package com.yourcompany.model;

import lombok.Builder;
import lombok.Data;
import java.util.List;

@Data
@Builder
public class DateIdeaRequest {
    private String query;
    private UserLocationDto userLocation;
    private ConstraintsDto constraints;
}

@Data
@Builder
public class UserLocationDto {
    private double lat;
    private double lon;
}

@Data
@Builder
public class ConstraintsDto {
    private String city;
    private Integer budgetTier;
    private Integer hours;
    private Boolean indoor;
    private List<String> categories;
}

@Data
@Builder
public class DateIdeaResponse {
    private String text;
    private String summary;
    private List<DateOption> options;
}

@Data
@Builder
public class DateOption {
    private String title;
    private List<String> categories;
    private String price;
    private int durationMin;
    private String whyItFits;
    private String logistics;
    private String website;
    private String source;
    private EntityReference primaryEntity;
    private List<EntityReference> relatedEntities;
}

@Data
@Builder
public class EntityReference {
    private String id;
    private String type;
    private String title;
    private String url;
}
```

#### REST Controller

```java
package com.yourcompany.controller;

import com.yourcompany.model.*;
import com.yourcompany.service.AiOrchestratorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.concurrent.CompletableFuture;

@RestController
@RequestMapping("/api/ai")
public class AiOrchestratorController {
    
    @Autowired
    private AiOrchestratorService aiOrchestratorService;
    
    @PostMapping("/date-ideas")
    public CompletableFuture<ResponseEntity<DateIdeaResponse>> getDateIdeas(
            @RequestBody DateIdeaRequest request) {
        
        return aiOrchestratorService.getDateIdeas(request)
                .thenApply(ResponseEntity::ok)
                .exceptionally(throwable -> ResponseEntity.internalServerError().build());
    }
}
```

### 5. Usage Example

```java
@Service
public class DatePlanningService {
    
    @Autowired
    private AiOrchestratorService aiOrchestratorService;
    
    public CompletableFuture<DateIdeaResponse> planRomanticDate(String city, int budget) {
        DateIdeaRequest request = DateIdeaRequest.builder()
                .query("I want a romantic date idea for couples")
                .constraints(ConstraintsDto.builder()
                        .city(city)
                        .budgetTier(budget)
                        .categories(List.of("romantic"))
                        .build())
                .build();
        
        return aiOrchestratorService.getDateIdeas(request)
                .thenApply(response -> {
                    // Log the response
                    logger.info("AI Response: {}", response.getText());
                    
                    // Process entity references for frontend
                    response.getOptions().forEach(option -> {
                        logger.info("Option: {} with {} related entities", 
                                option.getTitle(), 
                                option.getRelatedEntities().size());
                        
                        // You can now create clickable links in your frontend
                        option.getRelatedEntities().forEach(entity -> {
                            logger.info("  - {}: {} -> {}", 
                                    entity.getType(), 
                                    entity.getTitle(), 
                                    entity.getUrl());
                        });
                    });
                    
                    return response;
                });
    }
}
```

## Option 2: Java HTTP Client (REST API)

If you prefer HTTP over gRPC, you can use the REST API wrapper:

### 1. HTTP Client Implementation

```java
package com.yourcompany.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

@Service
public class AiOrchestratorHttpService {
    
    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    
    public AiOrchestratorHttpService() {
        this.webClient = WebClient.builder()
                .baseUrl("http://localhost:8000")
                .build();
        this.objectMapper = new ObjectMapper();
    }
    
    public Mono<DateIdeaResponse> getDateIdeas(DateIdeaRequest request) {
        // Convert to HTTP request format
        HttpChatRequest httpRequest = HttpChatRequest.builder()
                .messages(List.of(HttpChatMessage.builder()
                        .role("user")
                        .content(request.getQuery())
                        .build()))
                .constraints(request.getConstraints())
                .userLocation(request.getUserLocation())
                .build();
        
        return webClient.post()
                .uri("/api/chat")
                .bodyValue(httpRequest)
                .retrieve()
                .bodyToMono(HttpChatResponse.class)
                .map(this::convertToDateIdeaResponse);
    }
    
    private DateIdeaResponse convertToDateIdeaResponse(HttpChatResponse httpResponse) {
        return DateIdeaResponse.builder()
                .text(httpResponse.getText())
                .summary(httpResponse.getStructured() != null ? 
                        httpResponse.getStructured().get("summary").toString() : null)
                .options(httpResponse.getOptions())
                .build();
    }
}
```

### 2. Health Check

```java
@RestController
@RequestMapping("/api/health")
public class HealthController {
    
    @Autowired
    private AiOrchestratorService aiOrchestratorService;
    
    @GetMapping("/ai-orchestrator")
    public ResponseEntity<Map<String, String>> checkAiOrchestrator() {
        try {
            // Simple ping test
            DateIdeaRequest testRequest = DateIdeaRequest.builder()
                    .query("ping")
                    .build();
            
            CompletableFuture<DateIdeaResponse> future = aiOrchestratorService.getDateIdeas(testRequest);
            
            // Wait for response (with timeout)
            future.get(5, TimeUnit.SECONDS);
            
            return ResponseEntity.ok(Map.of("status", "healthy"));
        } catch (Exception e) {
            return ResponseEntity.status(503)
                    .body(Map.of("status", "unhealthy", "error", e.getMessage()));
        }
    }
}
```

## Configuration

### Application Properties

```yaml
# application.yml
ai:
  orchestrator:
    grpc:
      host: localhost
      port: 50051
    http:
      base-url: http://localhost:8000
    timeout: 30s

logging:
  level:
    com.yourcompany.service.AiOrchestratorService: DEBUG
    io.grpc: WARN
```

### Configuration Class

```java
package com.yourcompany.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import lombok.Data;

@Configuration
@ConfigurationProperties(prefix = "ai.orchestrator")
@Data
public class AiOrchestratorConfig {
    private Grpc grpc = new Grpc();
    private Http http = new Http();
    private String timeout = "30s";
    
    @Data
    public static class Grpc {
        private String host = "localhost";
        private int port = 50051;
    }
    
    @Data
    public static class Http {
        private String baseUrl = "http://localhost:8000";
    }
}
```

## Testing

### Unit Test

```java
package com.yourcompany.service;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

import java.util.List;
import java.util.concurrent.CompletableFuture;

@SpringBootTest
@TestPropertySource(properties = {
    "ai.orchestrator.grpc.host=localhost",
    "ai.orchestrator.grpc.port=50051"
})
class AiOrchestratorServiceTest {
    
    @Test
    void testGetDateIdeas() throws Exception {
        AiOrchestratorService service = new AiOrchestratorService();
        
        DateIdeaRequest request = DateIdeaRequest.builder()
                .query("romantic date in New York")
                .constraints(ConstraintsDto.builder()
                        .city("New York")
                        .budgetTier(2)
                        .categories(List.of("romantic"))
                        .build())
                .build();
        
        CompletableFuture<DateIdeaResponse> future = service.getDateIdeas(request);
        DateIdeaResponse response = future.get();
        
        assertThat(response).isNotNull();
        assertThat(response.getText()).isNotEmpty();
        assertThat(response.getOptions()).isNotEmpty();
        
        // Test entity references
        DateOption firstOption = response.getOptions().get(0);
        assertThat(firstOption.getPrimaryEntity()).isNotNull();
        assertThat(firstOption.getRelatedEntities()).isNotEmpty();
        
        service.shutdown();
    }
}
```

## Error Handling

```java
@Component
public class AiOrchestratorErrorHandler {
    
    private static final Logger logger = LoggerFactory.getLogger(AiOrchestratorErrorHandler.class);
    
    public DateIdeaResponse handleError(Throwable throwable, DateIdeaRequest request) {
        logger.error("AI Orchestrator error for request: {}", request.getQuery(), throwable);
        
        // Return fallback response
        return DateIdeaResponse.builder()
                .text("I'm sorry, I'm having trouble generating date ideas right now. Please try again later.")
                .summary("Service temporarily unavailable")
                .options(List.of())
                .build();
    }
}
```

## Docker Integration

### Dockerfile for your Java app

```dockerfile
FROM openjdk:17-jdk-slim

WORKDIR /app

COPY target/your-app.jar app.jar

# Wait for AI orchestrator to be ready
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

EXPOSE 8080

CMD ["/wait-for-it.sh", "ai-orchestrator:50051", "--", "java", "-jar", "app.jar"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  ai-orchestrator:
    build: ./ai_orchestrator
    ports:
      - "50051:50051"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", "python3", "test_backend_integration.py"]
      interval: 30s
      timeout: 10s
      retries: 3

  java-backend:
    build: .
    ports:
      - "8080:8080"
    environment:
      - AI_ORCHESTRATOR_GRPC_HOST=ai-orchestrator
      - AI_ORCHESTRATOR_GRPC_PORT=50051
    depends_on:
      ai-orchestrator:
        condition: service_healthy
```

That's it! Your Java backend can now connect to the AI orchestrator and get responses with clickable entity references. The system will provide structured data that your frontend can render as interactive elements.
