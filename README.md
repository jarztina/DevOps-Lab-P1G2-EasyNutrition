**VeriFact**
AI Claim Checker Application
LAB P1 G2
Justin Ang , Gabriel Lee, Han Ni, Sebastian Goh, Jia Le, Jovan Ng


1. Problem Statement and Target Users
What real-world problem does your application aim to solve?
As technology and artificial intelligence continue to evolve, fraudulent information/hoax is increasingly generated and distributed across social platforms to drive online engagement. These often reuse real events with wrong/altered details some of these examples are (wrong dates, wrong numbers, outdated news, etc). 

Most existing fact checking tools only give a single flat verdict such as “FALSE” without clearly explaining which specific details are incorrect. They may also not indicate whether the content itself could be AI-generated or whether the same claim has circulated previously. This will make it difficult for users to recognise if the information is fraudulent or a hoax.

Our application checks a submitted claim against web sources, breaks down exactly which facts match or doesn't and tracks recurring claims with our database so users can spot these patterns of repeated hoax in the future.


 
Who are the intended users of the application?
Social media users (especially students and young adults who often get news from social media such as tt, x, instagram)
News professionals
Educators
Other relevant users who want a quick, reliable, and easy-to-understand claim check supported by sources rather than simply receiving a true/false answer. 


 2. User Inputs 
What information or data will users provide to the system? 
Local Image
Pasted text of claims
Link of news articles

3. Use of AI 
How will AI be utilized within the application? 
 AI will be used to analyze and evaluate information provided by users. The AI will identify key claims and compare them against reliable sources and evidence.
The AI will have persistent memory of previously checked claims. This will help in identifying recurring claims and suspicious patterns.
To generate a list of sources from the internet with links

What outputs, insights, or recommendations will the AI generate from the user inputs? 
Verification results
Summarized source and evidence
Recurring claim detection
Manipulation pattern flags
Confidence indicator
Risk Score

4. Business Rules 
What business rules, validations, or decision-making logic will be applied to the AI-generated outputs? 
Manipulation pattern detection
A claim will only be marked verified or false if at least two independent sources agree, else it would be marked as “unable to verify”
Source Credibility is weighted, major outlets will carry more weight than unverified and un-credible sources
If a submitted claim closely matches one already stored in the database, it would be flagged as recurring claim instead of being processed as new



Repo Link: 
https://github.com/jarztina/DevOps-Lab-P1G2-VeriFact
