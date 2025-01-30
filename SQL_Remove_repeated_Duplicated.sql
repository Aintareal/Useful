; WITH addresses_split AS (
	SELECT [Account Id],[Mailing Street]
	, TRIM(SS.value) CommaValue, SS.ordinal CommaOrdinal
	--, SSS.value SpaceValue, SSS.ordinal SpaceOrdinal
	FROM #FY24UKNEWSLETTER F
	CROSS APPLY dbo.ufn_SplitOrdered(REPLACE(TRIM(F.[Mailing Street]),'"',''),',') SS
	--CROSS APPLY dbo.ufn_SplitOrdered(TRIM(SS.value),' ') SSS
), comma_phrases_to_remove AS (
	SELECT DISTINCT A1.[Account Id], A1.[Mailing Street], A2.CommaValue, A2.CommaOrdinal
	FROM addresses_split A1
	JOIN addresses_split A2 ON A1.[Account Id] = A2.[Account Id] AND (A1.CommaValue = A2.CommaValue OR A1.CommaValue+' '+A1.CommaValue = A2.CommaValue) AND A1.CommaOrdinal < A2.CommaOrdinal
), cleaned_addrs AS (
	SELECT A.[Account Id], A.[Mailing Street], STRING_AGG(A.CommaValue,', ') WITHIN GROUP (ORDER BY A.CommaOrdinal) [New Mailing Street]
	FROM addresses_split A
	LEFT JOIN comma_phrases_to_remove R ON A.[Account Id] = R.[Account Id] AND A.CommaValue = R.CommaValue AND A.CommaOrdinal = R.CommaOrdinal
	WHERE A.[Account Id] IN (SELECT [Account Id] FROM comma_phrases_to_remove)
	AND R.[Account Id] IS NULL
	AND A.CommaValue <> ''
	GROUP BY A.[Account Id], A.[Mailing Street]
)
--SELECT * FROM cleaned_addrs
UPDATE F
SET [Mailing Street] = C.[New Mailing Street]
FROM #FY24UKNEWSLETTER F
JOIN cleaned_addrs C ON F.[Account Id] = C.[Account Id]
