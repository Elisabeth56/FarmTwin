# FarmTwin — Master Product Knowledge

> This document is the frozen source of truth for FarmTwin. It is copied verbatim from the approved Product Knowledge. Do not edit sections 1–41 without an accompanying decision in `DECISIONS.md`.

You are the Product Knowledge Brain, Product Strategist, and Source of Truth for FarmTwin.
Everything you produce must remain consistent with this document.
You must understand both:

1. The product we are building.
2. The hackathon we are building it for.

Do not optimize one while ignoring the other.

## 1. PROJECT

Product name: FarmTwin
Positioning: An offline AI digital twin for farms.
Core tagline:
Know your farm. Predict what's next. Protect your harvest.
FarmTwin is being developed for the Africa Deep Tech Challenge 2026 — The Laptop LLM Challenge.
The project is primarily an Agriculture-domain on-device AI application.

## 2. THE PRODUCT IN ONE SENTENCE

FarmTwin creates a digital representation of an individual farm and uses a lightweight local language model, combined with locally stored agricultural knowledge and farm-specific records, to help farmers understand risks and make better agricultural decisions.

## 3. THE PROBLEM

Farmers face crop losses from interacting factors including:

- Weather
- Drought
- Flooding
- Pests
- Crop diseases
- Soil conditions
- Crop timing
- Environmental stress
- Poor access to timely information
- Limited agricultural extension capacity

The problem is not simply that farmers know nothing about agriculture.
The deeper problem is:
Agricultural knowledge is fragmented and generalized, while farm decisions are local, specific, and time-sensitive.
A farmer may be able to obtain a weather forecast, crop guide, disease information, or extension advice.
But the farmer still needs to answer:
What does all of this mean for my farm right now?
FarmTwin addresses that decision gap.

## 4. EVIDENCE FOR THE PROBLEM

Nigeria-specific World Bank analysis found that partial crop losses increased from approximately 6% of plots in 2018/19 to more than 20% of plots in 2023/24.
In Nigeria's Northeast, partial crop losses exceeded 40% of plots in 2023/24.
Weather and environmental shocks accounted for nearly two-thirds of partial crop losses in Nigeria in 2023/24.
Nigeria's National Agricultural Extension and Research Liaison Services has also reported severe limitations in extension coverage, including an average extension-agent-to-farmer ratio of approximately 1:6,000 in 2021.
These statistics demonstrate that agricultural losses and access to individualized agricultural guidance are significant problems.
Use these figures accurately.
Never say:
"Nigerian farmers lose 20% of their crops."
Instead say:
"More than 20% of Nigerian agricultural plots experienced partial crop losses in the 2023/24 season."
Never imply that FarmTwin will eliminate these losses.
The responsible claim is:
Better farm-specific information and earlier decision support may help reduce avoidable losses.

## 5. WHY FARMTWIN EXISTS

Existing agricultural technologies often solve individual problems:

- Weather apps provide weather.
- Crop calendars provide crop timing.
- Disease classifiers identify possible diseases.
- Agricultural chatbots answer questions.
- Extension services provide expertise.
- Farm management systems store records.

FarmTwin combines these concepts around a single object:
The individual farm.
A generic agricultural assistant knows about maize.
FarmTwin knows:
This farm grows maize, was planted on a particular date, is currently at a particular growth stage, has particular environmental conditions, and has a history that changes the relevance of agricultural advice.
That is the core product differentiation.

## 6. DIGITAL TWIN

The farm is represented as a living digital state.
A FarmTwin may contain:

```text
Farm
├── Location
├── Area
├── Boundaries
├── Fields
│   ├── Crop
│   ├── Variety
│   ├── Planting date
│   ├── Growth stage
│   ├── Soil
│   └── Health
├── Weather context
├── Agricultural history
├── Farm observations
├── Risks
├── Recommendations
├── Yield projections
└── Harvest history
```

The digital twin is not simply a dashboard.
The farm state must materially influence what the AI says.

## 7. CORE INTELLIGENCE LOOP

FarmTwin follows:

```text
OBSERVE
   ↓
UNDERSTAND
   ↓
PREDICT
   ↓
RECOMMEND
   ↓
ACT
   ↓
LEARN
```

Example:
A weather event is detected.
↓
The farm state is updated.
↓
The system knows which crop and growth stage are affected.
↓
Relevant agricultural knowledge is retrieved.
↓
The local language model reasons over the farm context.
↓
Farm-specific advice is generated.
↓
The farmer acts.
↓
That activity can become part of the farm's historical record.

## 8. PRIMARY USER

The primary user is:

- Smallholder farmer
- Commercial farmer
- Farm manager

Secondary users may include:

- Agricultural extension officers
- Cooperatives
- Agribusinesses
- NGOs
- Government agriculture programs
- Agricultural researchers

The MVP is primarily designed around the farmer/farm manager.

## 9. FARM DATA

Each farm should be able to capture:

Farm

- Name
- Location
- Size
- Boundaries

Crop

- Crop type
- Variety
- Planting date
- Growth stage
- Expected harvest

Soil
Where available:

- Soil type
- pH
- Nutrient condition
- Moisture

Weather

- Rainfall
- Temperature
- Humidity
- Wind
- Forecast
- Historical weather

Farm history

- Planting
- Fertilization
- Irrigation
- Pest observations
- Disease observations
- Harvests
- Other interventions

## 10. FARM-SPECIFIC REASONING

The local model should not simply answer generic agricultural questions.
It should reason over:

```text
User question
+
Farm state
+
Retrieved agricultural knowledge
+
Relevant environmental information
```

Example:
Generic AI:
"Maize generally grows through vegetative, flowering, and maturity stages."
FarmTwin:
"Your maize was planted on June 12 and is currently in its vegetative stage. Based on the agricultural information available for this crop stage, focus on monitoring plant vigor and environmental stress over the next few weeks."
Farm-specific reasoning is a core product requirement.

## 11. LOCAL-FIRST AI

The competition requires the core language-model application to operate locally.
FarmTwin therefore uses:

```text
Farm Context
     +
Local Agricultural Knowledge
     ↓
Offline Retrieval
     ↓
Context Assembly
     ↓
Local GGUF Model
     ↓
llama.cpp
     ↓
Agricultural Reasoning
```

The core intelligence must not depend on:

- OpenAI API
- Claude API
- Gemini API
- Cloud inference
- Cloud embeddings
- Remote vector databases

The system should continue to function without internet access.

## 12. HACKATHON HARDWARE CONSTRAINTS

FarmTwin is being optimized for the ADTC Standard Laptop environment.
Target hardware:

- 8 GB RAM
- Integrated graphics
- CPU inference
- Ubuntu 22.04
- x86-64
- 256 GB SSD

The challenge imposes a 7 GB model-memory ceiling.
Exceeding the memory limit or crashing out of memory can result in disqualification.
Therefore:
Performance and memory constraints are first-class product requirements.

## 13. HACKATHON SCORING

The competition evaluates:

- 50% Accuracy
- 30% Throughput
- 20% Efficiency
- Thermal penalty where applicable

Therefore the project's priority order is:

1. Agricultural/model accuracy
2. Farm-specific reasoning quality
3. Throughput
4. Memory efficiency
5. Thermal stability
6. African contextual depth
7. UI polish

A beautiful dashboard cannot compensate for a weak local model.

## 14. LOCAL MODEL

The exact model is not predetermined.
Candidate compact open-source model families may include:

- Llama
- Qwen
- Mistral
- Phi
- Other suitable open-source models

The final model must be selected through real benchmarking.
Evaluate:

- Agricultural accuracy
- Reasoning quality
- Context handling
- Retrieval grounding
- Tokens per second
- Peak memory
- Thermal behavior

Never invent model benchmark results.

## 15. GGUF AND LLAMA.CPP

The final model must be compatible with the required local inference environment.
Use:
GGUF
for model format.
Use:
llama.cpp
for local inference.
The development architecture should treat the inference engine as a swappable component where practical, but the submission implementation must support the required runtime.

## 16. OFFLINE RAG

FarmTwin's primary cross-disciplinary integration is:
Offline Retrieval-Augmented Generation over agricultural knowledge and farm records.
The knowledge layer should contain information such as:

- Crop lifecycle
- Crop management
- Crop diseases
- Crop pests
- Soil information
- Weather/agriculture relationships
- Harvest information
- Nigerian agricultural practices
- African agricultural context

The system should retrieve relevant information locally and provide it to the model.
Each retrieval result should retain source metadata.
The model should be able to distinguish between:

- Farm facts
- Retrieved agricultural knowledge
- Predictions
- Recommendations

## 17. FARM RECORD RETRIEVAL

The RAG layer should retrieve both:
General agricultural knowledge
Example:
Maize is susceptible to certain fungal diseases under particular environmental conditions.
and:
Farm-specific records
Example:
Farmer reported heavy rainfall on Field B three days ago.
The combination is important.
The model reasons over both.

## 18. DETERMINISTIC LOGIC

Do not force the language model to calculate everything.
Use deterministic code for:

- Date calculations
- Crop timelines
- Unit conversions
- Simple numerical calculations
- Farm state
- Known thresholds
- Data normalization

Then let the LLM reason over and explain those results.
For example:

```text
Planting date
+
Crop duration assumptions
=
Expected harvest window
```

The model should explain the result rather than invent the calculation.

## 19. CROP LIFECYCLE

FarmTwin should model crop stages.
Typical structure:

```text
Planting
   ↓
Germination
   ↓
Vegetative
   ↓
Flowering
   ↓
Maturity
   ↓
Harvest
```

The exact duration depends on:

- Crop
- Variety
- Location
- Conditions
- Agricultural assumptions

Never make unsupported universal claims.
For long-duration crops such as yam, FarmTwin should support longer production timelines and seasonal planning.

## 20. WEATHER INTELLIGENCE

Weather data should become agricultural intelligence.
Do not merely display:
"Rain expected tomorrow."
Instead, where enough context exists, FarmTwin should explain:
"Rain is expected within the next 48 hours. Given your crop stage and current farm conditions, inspect drainage and reconsider irrigation timing."
The system should connect:

```text
Weather
+
Crop
+
Growth stage
+
Farm context
=
Agricultural implication
```

## 21. RISK ENGINE

FarmTwin may identify risks such as:

- Excess rainfall
- Drought
- Heat stress
- Flooding
- Pest pressure
- Disease risk
- Nutrient deficiency
- Crop-stage issues

Risk outputs should contain:

- Risk
- Reason
- Severity
- Time sensitivity
- Supporting context
- Recommendation
- Confidence where appropriate

## 22. RECOMMENDATION ENGINE

Recommendations should be practical and actionable.
A recommendation should answer:
WHAT
What should the farmer do?
WHY
Why is it recommended?
WHEN
How urgently should it be done?
RISK
What is the likely consequence if ignored?
Example:
Inspect Field B
Recent rainfall and elevated humidity may increase conditions associated with fungal disease.
Recommended: Inspect affected plants within 24 hours.
Priority: High.
Avoid unsupported certainty.

## 23. DISEASE IMAGE ANALYSIS

FarmTwin may support crop-image analysis.
Possible workflow:

```text
Crop image
   ↓
Vision model
   ↓
Potential diagnosis
   ↓
Confidence
   ↓
Agricultural context
   ↓
Recommendation
```

Disease detection is a supporting feature, not the core competition feature.
Do not spend development time on it at the expense of the local language model, RAG, and benchmark performance.

## 24. YIELD PREDICTION

Yield prediction is a future or supporting capability.
Potential inputs:

- Farm size
- Crop
- Variety
- Growth stage
- Historical performance
- Weather
- Soil
- Reference agronomic data

Outputs should be framed as estimates.
Never claim a validated prediction accuracy that has not been measured.

## 25. AFRICAN CONTEXT

FarmTwin should be clearly relevant to African agricultural realities.
Important considerations:

- Smallholder farming
- Intermittent connectivity
- Low-resource hardware
- Local agricultural practices
- Nigerian crops
- African extension systems
- Affordable/on-device computing

The product should demonstrate that useful AI does not necessarily require expensive cloud infrastructure.

## 26. AFRICAN LANGUAGE BONUS

The competition provides an opportunity for an additional score/panel bonus through meaningful African-language functionality.
Potential languages include:

- Hausa
- Yoruba
- Igbo

A meaningful implementation would involve actual agricultural interaction, for example:

```text
Farmer question in Hausa/Yoruba/Igbo
        ↓
Local model
        ↓
Agricultural reasoning
        ↓
Response in the relevant language
```

Do not add superficial translation purely to claim the bonus.
Model accuracy remains more important.

## 27. USER EXPERIENCE

The primary product question is:
What is happening on my farm, what is likely to happen next, and what should I do?
The interface should therefore prioritize:

- Current farm state
- Crop state
- Risks
- Recommendations
- Crop timeline
- AI assistant
- Relevant context

Avoid a dashboard filled with meaningless analytics.
Every visualization should support a decision.

## 28. PRIMARY SCREENS

The MVP should contain only the screens necessary for the core experience.
Landing / onboarding
Explain what FarmTwin does.
Farm setup
Create or select a farm.
Farm dashboard
Show farm state, crops, alerts and recommendations.
Digital farm view
Show fields and relevant farm information.
Crop timeline
Show lifecycle and expected milestones.
Local AI assistant
Allow farm-specific agricultural questions.
Recommendation/risk views
Explain important detected issues.

## 29. DESIGN

FarmTwin should feel:

- Modern
- Trustworthy
- Technically sophisticated
- Agricultural
- Practical
- Accessible

It should not look like:

- A generic agricultural template
- A generic chatbot
- A generic SaaS dashboard
- A copy of another company's website

Design references may be supplied as screenshots and URLs.
Use them to derive:

- Layout
- Typography
- Spacing
- Visual hierarchy
- Navigation
- Interaction patterns
- Component style

Do not copy their branding, text, imagery, or identity.
All FarmTwin website copy should be generated from this Product Knowledge and the approved product strategy.

## 30. WEBSITE COPY

The product team does not need to manually write every line of website text.
The AI design/architecture workflow should generate appropriate:

- Hero headline
- Hero subheading
- CTAs
- Section headings
- Feature descriptions
- Dashboard labels
- Onboarding copy
- Alerts
- Recommendations
- Empty states
- Explanatory text

Copy must remain consistent with the actual product.
Do not make claims about functionality that has not been implemented.

## 31. MVP

The MVP must prove a complete intelligence loop:

```text
Create Farm
     ↓
Add Crop
     ↓
Generate Farm Context
     ↓
Retrieve Agricultural Knowledge
     ↓
Ask Farm-Specific Question
     ↓
Local LLM Reasons
     ↓
Generate Recommendation
     ↓
Display Result
```

This is more important than building many disconnected features.

## 32. DEMONSTRATION

The ideal demonstration tells one coherent story.
Example:

1. Create a Nigerian farm.
2. Add maize.
3. Add planting date.
4. Show the digital twin.
5. Show current crop stage.
6. Ask the local model a meaningful agricultural question.
7. Show retrieved agricultural context.
8. Show the model's reasoning/output.
9. Show the recommendation.
10. Demonstrate that the system still works offline.

The judge should understand:
This is a local agricultural AI system that understands a specific farm.

## 33. SUBMISSION STRATEGY

The submission must document:

- Problem
- Why it matters
- Product
- Architecture
- Constraints
- Design alternatives
- Final technical choices
- Model choice
- RAG
- llama.cpp
- GGUF
- Benchmarks
- Memory usage
- Throughput
- Offline operation
- African relevance
- Limitations
- Future work

Never fabricate:

- Metrics
- Benchmark scores
- User numbers
- Accuracy
- Adoption
- Deployment scale

Use actual implementation evidence.

## 34. TWO HACKATHON TEST PROMPTS

Our official test prompts should demonstrate FarmTwin's strongest capabilities.

**Test Prompt 1 — Farm-specific reasoning**

> You are advising a farmer managing a 2.5-hectare maize farm in Kaduna, Nigeria. The maize was planted on June 12 and is currently in the vegetative stage. Based on the farm information and agricultural knowledge available to you, identify the three most important risks or decisions the farmer should consider over the next two weeks. Explain the reasoning behind each recommendation and distinguish between known facts and predictions.

**Test Prompt 2 — RAG + farm records**

> A maize farmer in Kaduna has recorded recent heavy rainfall and increased humidity. The farm's crop is in the vegetative stage. Using the supplied farm records and relevant agricultural knowledge, assess the most likely agricultural risks, explain why they matter at this crop stage, and provide a prioritized action plan for the farmer. Identify the information you relied on.

These prompts should not be trivial.
They must demonstrate:

- Farm context
- Agricultural knowledge
- Retrieval
- Reasoning
- Actionable output

## 35. LONG-TERM VISION

FarmTwin may eventually integrate:

- Soil sensors
- Weather stations
- Satellite imagery
- Drones
- Market prices
- Farm machinery
- Agricultural finance
- Insurance
- Supply chains
- Cooperative data
- Government agricultural services

The long-term evolution is:

```text
Farm Monitoring
       ↓
Farm Intelligence
       ↓
Farm Optimization
       ↓
Semi-Autonomous Farm Management
```

But these are future capabilities.
They are not required for the MVP.

## 36. WHAT WE ARE NOT BUILDING NOW

Do not prioritize:

- Full agricultural marketplace
- Commodity trading
- Agricultural banking
- Insurance platform
- Drone control
- Autonomous machinery
- Full IoT infrastructure
- Complex satellite analytics
- Global agricultural coverage
- Massive supply-chain management

Unless a capability directly improves the hackathon benchmark or core demonstration, defer it.

## 37. PRODUCT DIFFERENTIATOR

FarmTwin is not:
AI + Agriculture.
It is:
A local agricultural intelligence system that reasons over a living digital representation of an individual farm.
The critical distinction is:
Generic AI knows agriculture.
FarmTwin knows the farmer's farm.

## 38. PRODUCT POSITIONING

Preferred product description:
FarmTwin is an offline AI digital twin for farms that combines farm-specific context with local agricultural knowledge to help farmers predict risks and make better decisions.
Preferred tagline:
Know your farm. Predict what's next. Protect your harvest.

## 39. SUCCESS CRITERIA

FarmTwin succeeds if it can demonstrate:

1. A real farm representation.
2. A local language model.
3. Offline agricultural knowledge retrieval.
4. Farm-specific reasoning.
5. Actionable agricultural recommendations.
6. Reproducible local execution.
7. Strong benchmark performance within the hardware constraints.

The ultimate question is:
Can FarmTwin identify meaningful agricultural information and turn it into a useful farm-specific decision using a local language model on constrained hardware?
That is the product.

## 40. DECISION RULE

When evaluating any new feature, ask:

1. Does it make the farm model more useful?
2. Does it improve agricultural reasoning?
3. Does it improve prediction or decision support?
4. Does it strengthen offline/local operation?
5. Does it improve the hackathon score?
6. Does it improve the demonstration?

If the answer is no to all of these, the feature should not be prioritized.

## 41. CORE PRINCIPLE

FarmTwin is not trying to build every agricultural technology.
It is demonstrating one specific proposition:
Useful agricultural AI can run locally, understand a specific farm, retrieve relevant agricultural knowledge, reason over that context, and provide actionable guidance on constrained hardware.
That proposition should guide every product, architecture, design, engineering, benchmark, and submission decision.
