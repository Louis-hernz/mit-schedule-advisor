# MIT Course Data Scraping Strategy

## Overview

Since we don't have direct access to MIT's internal course evaluation database, we'll scrape from **publicly available sources**. This document outlines ethical scraping practices and implementation.

## Data Sources (Ranked by Priority)

### 1. MIT OpenCourseWare (OCW) ⭐⭐⭐
**URL**: https://ocw.mit.edu/
**What**: Free course materials from MIT courses
**Scrapable Data**:
- Course descriptions
- Prerequisites
- Syllabi
- Lecture notes
- Course difficulty (implicit from content depth)

**Pros**:
- Completely public and free
- Well-structured HTML
- MIT encourages sharing
- No authentication required

**Implementation**:
```python
import aiohttp
from bs4 import BeautifulSoup

async def scrape_ocw_course(course_id: str):
    url = f"https://ocw.mit.edu/courses/{course_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract course info
            description = soup.find('div', class_='course-description')
            prerequisites = soup.find('div', class_='prerequisites')
            
            return {
                "description": description.text if description else "",
                "prerequisites": prerequisites.text if prerequisites else ""
            }
```

### 2. MIT Course Catalog (public pages) ⭐⭐⭐
**URL**: http://student.mit.edu/catalog/
**What**: Official course listings
**Scrapable Data**:
- Course numbers and titles
- Units
- When offered (Fall/Spring/IAP)
- Prerequisites
- Co-requisites
- General Institute Requirements (GIRs)

**Already have API for this** - use the MIT APIs you've been granted access to!

### 3. Reddit r/MIT ⭐⭐
**URL**: https://www.reddit.com/r/MIT/
**What**: Student discussions about courses
**Scrapable Data**:
- Student opinions
- Course difficulty
- Professor ratings
- Workload estimates
- "Which courses should I take?" threads

**Pros**:
- Real student experiences
- Recent data
- Public forum

**Cons**:
- Unstructured data
- Need sentiment analysis
- May be biased

**Implementation**:
```python
import praw  # Python Reddit API Wrapper

reddit = praw.Reddit(
    client_id="your_client_id",
    client_secret="your_secret",
    user_agent="MIT-Schedule-Advisor/0.1"
)

def scrape_course_discussions(course_id: str):
    subreddit = reddit.subreddit("MIT")
    posts = subreddit.search(f"{course_id}", limit=50)
    
    reviews = []
    for post in posts:
        if course_id.lower() in post.title.lower():
            reviews.append({
                "title": post.title,
                "content": post.selftext,
                "score": post.score,
                "comments": [c.body for c in post.comments[:10]]
            })
    
    return reviews
```

### 4. MIT Admissions Blogs
**URL**: https://mitadmissions.org/blogs/
**What**: Student-written blog posts
**Scrapable Data**:
- Course experiences
- Major advice
- Schedule planning tips

### 5. Course Evaluations (if publicly available)
**Check**: http://web.mit.edu/subject-evaluation/
**Note**: This may require MIT credentials. **DO NOT** scrape if login required.

## 📋 Ethical Scraping Guidelines

### Must Follow:
1. **Check `robots.txt`**
   ```python
   import requests
   response = requests.get("https://ocw.mit.edu/robots.txt")
   print(response.text)
   ```

2. **Add delays between requests** (1-2 seconds)
   ```python
   import asyncio
   await asyncio.sleep(1.5)
   ```

3. **Identify yourself in User-Agent**
   ```python
   headers = {
       "User-Agent": "MIT-Schedule-Advisor/0.1 (Educational Project; contact@example.com)"
   }
   ```

4. **Respect rate limits**
   - Max 1 request per second per domain
   - Use exponential backoff on errors

5. **Cache results**
   - Don't scrape the same page twice
   - Store in database/Redis

6. **Don't overload servers**
   - Scrape during off-peak hours
   - Use request queues

### Never Do:
- ❌ Scrape password-protected content
- ❌ Bypass authentication
- ❌ Ignore robots.txt
- ❌ Make rapid-fire requests
- ❌ Scrape personal student data
- ❌ Redistribute scraped data commercially

## Implementation: Course Evaluations Scraper

Create `backend/app/services/scraper/course_evaluations_scraper.py`:

```python
"""
Course Evaluations Scraper
Scrapes public course information ethically
"""
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from loguru import logger
import time

from app.core.config import get_settings

settings = get_settings()


class CourseEvaluationsScraper:
    """
    Ethical web scraper for MIT course data
    """
    
    def __init__(self):
        self.session = None
        self.request_delay = settings.SCRAPER_DELAY_SECONDS
        self.last_request_time = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    async def scrape_ocw_course(self, course_id: str) -> Dict[str, Any]:
        """
        Scrape course info from MIT OpenCourseWare
        
        Args:
            course_id: Course number (e.g., "6-006")
        
        Returns:
            Dictionary with course information
        """
        try:
            await self._rate_limit()
            
            # Convert 6.006 to 6-006 format for OCW
            ocw_id = course_id.replace(".", "-")
            url = f"https://ocw.mit.edu/courses/{ocw_id}"
            
            logger.info(f"Scraping OCW for {course_id}")
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"OCW page not found for {course_id}")
                    return {}
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                data = {
                    "course_id": course_id,
                    "source": "MIT OCW",
                    "description": "",
                    "prerequisites": "",
                    "materials_available": False
                }
                
                # Extract description
                desc = soup.find('div', class_='course-description')
                if desc:
                    data["description"] = desc.get_text(strip=True)
                
                # Extract prerequisites
                prereq = soup.find('h3', text='Prerequisites')
                if prereq and prereq.find_next_sibling():
                    data["prerequisites"] = prereq.find_next_sibling().get_text(strip=True)
                
                # Check if materials available
                materials = soup.find('div', class_='course-materials')
                if materials:
                    data["materials_available"] = True
                
                logger.info(f"✓ Scraped OCW data for {course_id}")
                return data
        
        except Exception as e:
            logger.error(f"Error scraping OCW for {course_id}: {e}")
            return {}
    
    async def scrape_reddit_reviews(
        self,
        course_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Scrape Reddit discussions about a course
        
        Note: Requires Reddit API credentials
        Returns empty list if not configured
        """
        try:
            # Check if Reddit credentials available
            # If not, return empty
            logger.info(f"Reddit scraping for {course_id} - not implemented yet")
            return []
            
            # TODO: Implement Reddit scraping with praw
            # import praw
            # reddit = praw.Reddit(...)
            # ...
        
        except Exception as e:
            logger.error(f"Error scraping Reddit for {course_id}: {e}")
            return []
    
    async def scrape_course_batch(
        self,
        course_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Scrape multiple courses efficiently
        
        Args:
            course_ids: List of course IDs to scrape
        
        Returns:
            Dictionary mapping course_id to scraped data
        """
        results = {}
        
        logger.info(f"Scraping {len(course_ids)} courses...")
        
        for i, course_id in enumerate(course_ids):
            try:
                data = await self.scrape_ocw_course(course_id)
                results[course_id] = data
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i + 1}/{len(course_ids)} courses")
            
            except Exception as e:
                logger.error(f"Error scraping {course_id}: {e}")
                results[course_id] = {}
        
        logger.info(f"✓ Completed scraping {len(course_ids)} courses")
        return results


async def scrape_and_index_courses(course_ids: List[str]):
    """
    Helper function to scrape courses and add to RAG
    """
    from app.services.rag.rag_service import RAGService
    
    rag = RAGService()
    
    async with CourseEvaluationsScraper() as scraper:
        results = await scraper.scrape_course_batch(course_ids)
        
        # Add scraped data to knowledge base
        for course_id, data in results.items():
            if data:
                await rag.add_knowledge(
                    doc_id=f"scraped_{course_id}",
                    text=f"Course {course_id} from OCW: {data.get('description', '')}",
                    metadata={
                        "type": "scraped_data",
                        "course_id": course_id,
                        "source": "OCW"
                    }
                )


# Example usage
if __name__ == "__main__":
    async def main():
        courses_to_scrape = ["6.006", "6.046", "18.06", "6.100A"]
        
        async with CourseEvaluationsScraper() as scraper:
            results = await scraper.scrape_course_batch(courses_to_scrape)
            
            for course_id, data in results.items():
                print(f"\n{course_id}:")
                print(f"  Description: {data.get('description', 'N/A')[:100]}...")
    
    asyncio.run(main())
```

## Alternative: Manual Data Collection

If scraping is too complex initially, you can:

1. **Manually add high-quality data** for popular courses
2. **Crowdsource** from MIT students
3. **Use MIT's official APIs** (which you already have access to!)
4. **Start with course catalog only**, add reviews later

## Scraping Schedule

### Phase 1 (MVP): Skip it!
- Use MIT APIs for course data
- Use GPT-4's knowledge for general advice
- Add a "tell us about this course" feature where users contribute

### Phase 2 (Enhancement):
- Scrape MIT OCW for 50 most popular courses
- Add to RAG knowledge base
- Improves course descriptions

### Phase 3 (Full Feature):
- Implement Reddit scraping
- Add sentiment analysis
- Generate difficulty ratings

## Legal Considerations

✅ **Legal to scrape**:
- Public MIT websites (OCW, course catalog)
- Public Reddit posts
- Any content in robots.txt "Allow" list

❌ **NOT legal to scrape**:
- Password-protected MIT sites
- Internal course evaluations
- Student personal data
- Content marked "noindex" or "nofollow"

## Final Recommendation

**For MVP deployment**: 
1. ✅ Use MIT APIs you have access to
2. ✅ Add MIT general knowledge manually
3. ❌ Skip scraping initially
4. 🔄 Add scraping in Phase 2 after core features work

This approach gets you to deployment faster and avoids legal/technical complications!
