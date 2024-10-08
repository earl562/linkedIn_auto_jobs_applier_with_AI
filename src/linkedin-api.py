from typing import Dict, List
from linkedin_api import Linkedin
from typing import Optional, Union, Literal
from urllib.parse import quote, urlencode
import logging
import json

# set log to all debug
logging.basicConfig(level=logging.INFO)


class LinkedInEvolvedAPI(Linkedin):
    def __init__(self, username, password):
        super().__init__(username, password)

    def search_jobs(
        self,
        keywords: Optional[str] = None,
        companies: Optional[List[str]] = None,
        experience: Optional[
            List[
                Union[
                    Literal["1"],
                    Literal["2"],
                    Literal["3"],
                    Literal["4"],
                    Literal["5"],
                    Literal["6"],
                ]
            ]
        ] = None,
        job_type: Optional[
            List[
                Union[
                    Literal["F"],
                    Literal["C"],
                    Literal["P"],
                    Literal["T"],
                    Literal["I"],
                    Literal["V"],
                    Literal["O"],
                ]
            ]
        ] = None,
        job_title: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
        location_name: Optional[str] = None,
        remote: Optional[List[Union[Literal["1"], Literal["2"], Literal["3"]]]] = None,
        listed_at=24 * 60 * 60,
        distance: Optional[int] = None,
        easy_apply: Optional[bool] = True,
        limit=-1,
        offset=0,
        **kwargs,
    ) -> List[Dict]:
        """Perform a LinkedIn search for jobs.

        :param keywords: Search keywords (str)
        :type keywords: str, optional
        :param companies: A list of company URN IDs (str)
        :type companies: list, optional
        :param experience: A list of experience levels, one or many of "1", "2", "3", "4", "5" and "6" (internship, entry level, associate, mid-senior level, director and executive, respectively)
        :type experience: list, optional
        :param job_type:  A list of job types , one or many of "F", "C", "P", "T", "I", "V", "O" (full-time, contract, part-time, temporary, internship, volunteer and "other", respectively)
        :type job_type: list, optional
        :param job_title: A list of title URN IDs (str)
        :type job_title: list, optional
        :param industries: A list of industry URN IDs (str)
        :type industries: list, optional
        :param location_name: Name of the location to search within. Example: "Kyiv City, Ukraine"
        :type location_name: str, optional
        :param remote: Filter for remote jobs, onsite or hybrid. onsite:"1", remote:"2", hybrid:"3"
        :type remote: list, optional
        :param listed_at: maximum number of seconds passed since job posting. 86400 will filter job postings posted in last 24 hours.
        :type listed_at: int/str, optional. Default value is equal to 24 hours.
        :param distance: maximum distance from location in miles
        :type distance: int/str, optional. If not specified, None or 0, the default value of 25 miles applied.
        :param easy_apply: filter for jobs that are easy to apply to
        :type easy_apply: bool, optional. Default value is True.
        :param limit: maximum number of results obtained from API queries. -1 means maximum which is defined by constants and is equal to 1000 now.
        :type limit: int, optional, default -1
        :param offset: indicates how many search results shall be skipped
        :type offset: int, optional
        :return: List of jobs
        :rtype: list
        """
        count = Linkedin._MAX_SEARCH_COUNT
        if limit is None:
            limit = -1

        query: Dict[str, Union[str, Dict[str, str]]] = {
            "origin": "JOB_SEARCH_PAGE_QUERY_EXPANSION"
        }
        if keywords:
            query["keywords"] = "KEYWORD_PLACEHOLDER"
        if location_name:
            query["locationFallback"] = "LOCATION_PLACEHOLDER"

        query["selectedFilters"] = {}
        if companies:
            query["selectedFilters"]["company"] = f"List({','.join(companies)})"
        if experience:
            query["selectedFilters"]["experience"] = f"List({','.join(experience)})"
        if job_type:
            query["selectedFilters"]["jobType"] = f"List({','.join(job_type)})"
        if job_title:
            query["selectedFilters"]["title"] = f"List({','.join(job_title)})"
        if industries:
            query["selectedFilters"]["industry"] = f"List({','.join(industries)})"
        if distance:
            query["selectedFilters"]["distance"] = f"List({distance})"
        if remote:
            query["selectedFilters"]["workplaceType"] = f"List({','.join(remote)})"
        if easy_apply:
            query["selectedFilters"]["applyWithLinkedin"] = "List(true)"

        query["selectedFilters"]["timePostedRange"] = f"List(r{listed_at})"
        query["spellCorrectionEnabled"] = "true"

        query_string = (
            str(query)
            .replace(" ", "")
            .replace("'", "")
            .replace("KEYWORD_PLACEHOLDER", keywords or "")
            .replace("LOCATION_PLACEHOLDER", location_name or "")
            .replace("{", "(")
            .replace("}", ")")
        )
        results = []
        while True:
            if limit > -1 and limit - len(results) < count:
                count = limit - len(results)
            default_params = {
                "decorationId": "com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-174",
                "count": count,
                "q": "jobSearch",
                "query": query_string,
                "start": len(results) + offset,
            }

            res = self._fetch(
                f"/voyagerJobsDashJobCards?{urlencode(default_params, safe='(),:')}",
                headers={"accept": "application/vnd.linkedin.normalized+json+2.1"},
            )
            data = res.json()

            elements = data.get("included", [])
            new_data = []
            for e in elements:
                trackingUrn = e.get("trackingUrn")
                if trackingUrn:
                    trackingUrn = trackingUrn.split(":")[-1]
                    e["job_id"] = trackingUrn
                if e.get("$type") == "com.linkedin.voyager.dash.jobs.JobPosting":
                    new_data.append(e)
                
            if not new_data:
                break
            results.extend(new_data)
            if (
                (-1 < limit <= len(results))
                or len(results) / count >= Linkedin._MAX_REPEATED_REQUESTS
            ) or len(elements) == 0:
                break

            self.logger.debug(f"results grew to {len(results)}")

        return results
    
    def get_fields_for_easy_apply(self,job_id:str) -> List[Dict]:
        """Get fields needed for easy apply jobs.

        :param job_id: Job ID
        :type job_id: str
        :return: Fields
        :rtype: dict
        """

        cookies = self.client.session.cookies.get_dict()
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])

        headers: Dict[str, str] = self._headers()
        

        headers["Accept"] = "application/vnd.linkedin.normalized+json+2.1"
        headers["csrf-token"] = cookies["JSESSIONID"].replace('"', "")
        headers["Cookie"] = cookie_str
        headers["Connection"] = "keep-alive"


        default_params = {
            "decorationId": "com.linkedin.voyager.dash.deco.jobs.OnsiteApplyApplication-67",
            "jobPostingUrn": f"urn:li:fsd_jobPosting:{job_id}",
            "q": "jobPosting",
        }

        default_params = urlencode(default_params)
        res = self._fetch(
            f"/voyagerJobsDashOnsiteApplyApplication?{default_params}",
            headers=headers,
            cookies=cookies,
        )

        match res.status_code:
            case 200:
                pass
            case 409:
                self.logger.error("Failed to fetch fields for easy apply job because already applied to this job!")
                return []
            case _:
                self.logger.error("Failed to fetch fields for easy apply job")
                return []

        try:
            data = res.json()
        except ValueError:
            self.logger.error("Failed to parse JSON response")
            return []
        
        form_components = []

        for item in data.get("included", []):
            if 'formComponent' in item:
                urn = item['urn']
                try:
                    title = item['title']['text']
                except TypeError:
                    title = urn
                
                form_component_type = list(item['formComponent'].keys())[0]
                form_component_details = item['formComponent'][form_component_type]
                
                component_info = {
                    'title': title,
                    'urn': urn,
                    'formComponentType': form_component_type,
                }
                
                if 'textSelectableOptions' in form_component_details:
                    options = [
                        opt['optionText']['text'] for opt in form_component_details['textSelectableOptions']
                    ]
                    component_info['selectableOptions'] = options
                elif 'selectableOptions' in form_component_details:
                    options = [
                        opt['textSelectableOption']['optionText']['text'] 
                        for opt in form_component_details['selectableOptions']
                    ]
                    component_info['selectableOptions'] = options
                
                form_components.append(component_info)

        return form_components

## EXAMPLE USAGE
if __name__ == "__main__":
    api: LinkedInEvolvedAPI = LinkedInEvolvedAPI(username="", password="")     
    jobs = api.search_jobs(keywords="Frontend Developer", location_name="Italia", limit=5, easy_apply=True, offset=1)
    for job in jobs:
        job_id: str = job["job_id"]

        fields = api.get_fields_for_easy_apply(job_id)
        for field in fields:
            print(field)

        

    