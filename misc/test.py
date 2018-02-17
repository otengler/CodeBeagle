from FullTextIndex import *

fti = FullTextIndex("D:\\qt473.dat.new")

fti.reorganizeKeywords()

del fti


def reorganizeKeywords (self):
    import collections

    logging.info("Analyzing keyword fragmentation")
    c = self.conn.cursor ()
    c.execute ("SELECT id, keyword FROM keywords")
    keywords = c.fetchall()
    count = len(keywords)
    notfragmented = 1
    prev = None
    for (_,keyword) in keywords:
        if prev and prev<keyword:
            notfragmented += 1
        prev = keyword

    if not count:
        logging.info("Datebase is empty. Nothing to do.")
        return

    fragmentation = 1.0 - float(notfragmented)/float(count)
    if fragmentation < 0.1:
        logging.info("Fragmentation is %2.1f which is below 10%. Nothing to do.", fragmentation)
        return

    logging.info("Fragmentation is %2.1f. Rebuilding keywords.", fragmentation)

    keywords.sort(key=lambda i: i[1])

    c.execute ("SELECT kwId, docId FROM kw2doc")
    associations = c.fetchall()

    mapCurrentAssocations = collections.defaultdict(list)
    for kwId,docId in associations:
        mapCurrentAssocations[kwId].append(docId)

    newDb = FullTextIndex (self.strDbLocation + ".new")
    cn = newDb.conn.cursor ()

    with newDb.conn:
        c.execute ("SELECT id,timestamp,fullpath FROM documents")
        result = c.fetchall()
        for id, timestamp, fullpath in result:
            cn.execute ("INSERT INTO documents (id,timestamp,fullpath) VALUES (?,?,?)", (id, timestamp, fullpath))

        c.execute ("SELECT docId,indexId FROM documentInIndex")
        result = c.fetchall()
        for docId, indexId in result:
            cn.execute ("INSERT INTO documentInIndex (docId,indexId) VALUES (?,?)", (docId, indexId))

        c.execute ("SELECT id,timestamp FROM indexInfo")
        result = c.fetchall()
        for id, timestamp in result:
            cn.execute ("INSERT INTO indexInfo (id,timestamp) VALUES (?,?)", (id, timestamp))

        #"documents", "documentInIndex", "indexInfo"
        #for table in ["keywords", "kw2doc", "documents", "documentInIndex", "indexInfo"]:
        #    logging.info ("Cleaning %s" % table)
        #    c.execute ("DELETE FROM %s" % table)

        logging.info ("Rebuilding keywords")
        for newId, (_,keyword) in enumerate(keywords):
            cn.execute ("INSERT INTO keywords (id,keyword) VALUES (?,?)", (newId+1,keyword))

        logging.info ("Rebuilding associations")
        for newId, (oldId,_) in enumerate(keywords):
            for docId in mapCurrentAssocations[oldId]:
                cn.execute ("INSERT INTO kw2doc (kwId,docId) VALUES (?,?)", (newId+1,docId))

    logging.info ("Reorganized keywords.")
