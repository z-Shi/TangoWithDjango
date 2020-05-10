import json
import requests
from abc import ABC, abstractmethod


def read_bing_key():
    bing_api_key = None
    try:
        with open('bing.key', 'r') as f:
            bing_api_key = f.readline().strip()
    except:
        try:
            with open('../bing.key', 'r') as f:
                bing_api_key = f.readline().strip()
        except:
            raise IOError('bing.key file not found')

    if not bing_api_key:
        raise KeyError('Bing key not found')

    return bing_api_key


class BingSearch(ABC):

    @abstractmethod
    def run_query(self, search_terms):
        pass


class BingSearchExternal(BingSearch):

    def run_query(self, search_terms):
        bing_key = read_bing_key()
        search_url = 'https://api.cognitive.microsoft.com/bing/v7.0/search'
        headers = {'Ocp-Apim-Subscription-Key': bing_key}
        params = {'q': search_terms, 'textDecorations': True, 'textFormat': 'HTML'}

        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        search_results = response.json()

        results = []
        for result in search_results['webPages']['value']:
            results.append({
                'title': result['name'],
                'link': result['url'],
                'summary': result['snippet']
            })

        return results


class BingSearchInternal(BingSearch):

    def run_query(self, search_terms):
        return [{'title': 'Cookies', 'link': 'https://www.google.co.uk', 'summary': 'Cookies...'}]


def main():
    external = BingSearchExternal()

    search_terms = input("Search for... ")
    search_results = external.run_query(search_terms)

    result_counter = 1
    for result in search_results:
        print("Result:", result_counter, "\n",
              "Title:", result['title'], "\n",
              "Link:", result['link'], "\n",
              "Summary:", result['summary'])
        result_counter += 1


if __name__ == '__main__':
    main()
