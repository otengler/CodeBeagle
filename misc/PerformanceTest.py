"""
Performance test for composite search phrases
"""

import time
import random
import fulltextindex.FullTextIndex as FullTextIndex

def taketime (func, *args):
    t1 = time.perf_counter()
    result = func(*args)
    t2 = time.perf_counter()
    print("%3.2f min" % ((t2-t1)/60.0,))
    return result

def genTestQueries(dbname):
    result = ""
    db = FullTextIndex.FullTextIndex(dbname)
    q = db.conn.cursor()
    q.execute("SELECT COUNT(*) FROM keywords")
    lenKWs = int(q.fetchone()[0])
    for i in range(200):
        tokenCount = random.randint(2, 7)
        setTokens = set()
        for j in range (tokenCount):
            id = random.randint(1, lenKWs)
            q.execute("SELECT keyword FROM keywords where id=:id",  {"id":id})
            token = q.fetchone()[0]
            setTokens.add(token)
        result = result + " ".join(setTokens) + "\n"
    return result

def performanceTest(db,  queries,  manualIntersect):
    for query in queries:
        queryParams = FullTextIndex.QueryParams(query)
        q = FullTextIndex.ContentQuery(queryParams)
        db.search(q,  None,  manualIntersect=manualIntersect)

def main():
    if 0:
        result = genTestQueries(r"D:\qt473.dat")
        with open("testQueries.txt", "w") as f:
            f.write(result)

    db = FullTextIndex.FullTextIndex(r"D:\qt473.dat")
    queries = [line.strip() for line in open("testQueries.txt").readlines()]
    taketime (performanceTest , db, queries,  False)
    taketime (performanceTest , db, queries,  True)

if __name__ == '__main__':
    main()


