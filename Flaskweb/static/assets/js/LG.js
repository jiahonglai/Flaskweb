let pageNum;
let map;
let markers = [];

window.onload = function () {
    initMap();
    getVisitorNum();
    getPageNum();
    listCountry();
}

if (window.name != "noReload") {
    window.name = "noReload";
    location.reload();
} else {
    window.name = "";
}

function getVisitorNum() {
    $.ajax({
        url: "/visitor_num",
        type: "GET",
        success: function (result) {
            $("#visitorNum").html(result);
        },
        error: function () {
            alert("获取访问量失败");
        }
    });
}

function getPageNum() {
    let cmdValue = document.getElementById("cmdValue");
    cmdValue = cmdValue.options[cmdValue.selectedIndex].value;
    let area = document.getElementById("area");
    area = area.options[area.selectedIndex].value;
    let country = document.getElementById("country");
    country = country.options[country.selectedIndex].value;
    $.ajax({
        url: "/page_num",
        type: "POST",
        dataType: "json",
        data: {
            data: JSON.stringify({
                "cmdValue": cmdValue,
                "area": area,
                "country": country,
            })
        },
        success: function (result) {
            pageNum = result;
            $("#totalPage").html(pageNum);
            showPage(1);
        },
        error: function () {
            alert("获取页数失败");
        }
    });
}

function showInfo(page) {
    let cmdValue = document.getElementById("cmdValue");
    cmdValue = cmdValue.options[cmdValue.selectedIndex].value;
    let area = document.getElementById("area");
    area = area.options[area.selectedIndex].value;
    let country = document.getElementById("country");
    country = country.options[country.selectedIndex].value;
    $.ajax({
        url: "/page",
        type: "POST",
        dataType: "json",
        data: {
            data: JSON.stringify({
                "cmdValue": cmdValue,
                "area": area,
                "country": country,
                "page": page
            })
        },
        success: function (result) {
            if (markers.length > 0) { //清除之前的标记点
                for (let i in markers) markers[i].remove();
                markers = [];
            }
            let msg = "";
            for (let index in result) {
                let record = result[index];
                msg += "<tr>";
                msg += "<td style='text-align: center;height: 50px;vertical-align: middle'><input type='checkbox' ";
                msg += "value='" + record['URL'] + "|" + record['routerValue'] + "' ";
                msg += "style='-webkit-appearance: button' name='routers'></td>";
                let IP = record['URL'].split("http://");
                if (IP.length == 1) {
                    IP = record['URL'].split("https://");
                }
                IP = IP[1];
                msg += "<td style='text-align: center;vertical-align: middle'>" + "<a href='" + record['URL'] + "'>" + IP +
                    "</a></td>";
                msg += "<td style='text-align: center;vertical-align: middle'>" + record['routerValue'] + "</td>";
                msg += "<td style='text-align: center;vertical-align: middle'>" + record['AS'] + "</td>";
                msg += "<td style='text-align: center;vertical-align: middle'>" + record['country'] + "</td>";
                msg += "<td style='text-align: center;vertical-align: middle'>" + record['city'] + "</td>";
                msg +=
                    "<td style='text-align: center;vertical-align: middle'><img src='static/images/tick.png' width='50px' alt='√'></td>";
                msg += "</tr>";
                if (record['longitude'] != null) {
                    let marker = new mapboxgl.Marker().setLngLat([record['longitude'], record['latitude']]).addTo(map);
                    markers.push(marker);
                }
            }
            $("#info").html(msg);
        },
        error: function () {
            alert("获取搜索数据失败");
        }
    });
}

function query(key) {
    let routers = document.getElementsByName("routers");
    keys = [];
    checkedNum = 0;
    for (let index in routers) {
        if (routers[index].checked) {
            ++checkedNum;
            if (checkedNum == 6) {
                alert("请勿选择超过5个测量点");
                return;
            }
            keys.push(routers[index].value);
        }
    }
    let cmdValue = document.getElementById("cmdValue");
    cmdValue = cmdValue.options[cmdValue.selectedIndex].value;
    let parameter = document.getElementById("parameter").value;
    if (parameter == "") {
        alert("请输入参数");
        return;
    }
    let type = document.getElementById("type").value;
    $.ajax({
        type: "POST",
        url: "/api/query",
        data: {
            data: JSON.stringify({
                "keys": keys,
                "cmdValue": cmdValue,
                "parameter": parameter,
                "type": type,
                "showHtml": "True",
            })
        },
        dataType: "json",
        beforeSend: function () {
            document.getElementById("prompt").hidden = false;
            document.getElementById("content").hidden = true;
        },
        success: function (response) {
            if (response['Info'] != null) {
                alert(response['Info']);
                window.location.href = "/";
            }
            else window.location.href = response;
        },
        error: function () {
            alert("查询失败");
            window.location.href = "/";
        }
    });
}

function showPage(page) {
    let htmlText = "<li onclick='showPage(1)'><a href=\"#\"> << </a></li>";
    let prePage = Math.max(page - 1, 1);
    htmlText += "<li onclick='showPage(" + prePage + ")'><a href=\"#\"> < </a></li>";
    if (pageNum < 5) {
        for (let i = 1; i <= pageNum; ++i) {
            htmlText += "<li onclick='showPage(" + i + ")' ";
            if (i == page) htmlText += "class='active'";
            htmlText += "><a href=\"#\">" + i + "</a></li>";
        }
    } else {
        let leftNum = page - 1;
        if (leftNum < 2) {
            for (let i = 1; i <= 5; ++i) {
                htmlText += "<li onclick='showPage(" + i + ")' ";
                if (i == page) htmlText += "class='active'";
                htmlText += "><a href=\"#\">" + i + "</a></li>";
            }
        }
        let rightNum = pageNum - page;
        if (rightNum < 2) {
            for (let i = pageNum - 4; i <= pageNum; ++i) {
                htmlText += "<li onclick='showPage(" + i + ")' ";
                if (i == page) htmlText += "class='active'";
                htmlText += "><a href=\"#\">" + i + "</a></li>";
            }
        }
        if (leftNum > 1 && rightNum > 1) {
            for (let i = page - 2; i <= page + 2; ++i) {
                htmlText += "<li onclick='showPage(" + i + ")' ";
                if (i == page) htmlText += "class='active'";
                htmlText += "><a href=\"#\">" + i + "</a></li>";
            }
        }
    }
    let nextPage = Math.min(page + 1, pageNum);
    htmlText += "<li onclick='showPage(" + nextPage + ")'><a href=\"#\"> > </a></li>";
    htmlText += "<li onclick='showPage(" + pageNum + ")'><a href=\"#\"> >> </a></li>";
    $("#pagination").html(htmlText);
    showInfo(page);
}

function listCountry() {
    let area = document.getElementById("area");
    area = area.options[area.selectedIndex].value;
    $.ajax({
        url: "/country",
        type: "GET",
        data: { 'area': area },
        dataType: "json",
        success: function (countryList) {
            let countryOption = document.getElementById("country");
            countryOption.options.length = 1;
            for (let i in countryList) {
                let country = countryList[i];
                let option = document.createElement("option");
                option.value = country;
                option.text = country;
                countryOption.options.add(option);
            }
        },
        error: function () {
            alert("国家数据加载出错！");
        }
    });
}

function initMap() {
    mapboxgl.accessToken = 'pk.eyJ1IjoiY2hyaXNld2Fybm5lciIsImEiOiJja3NwbjF6bjUwNGJtMm5rdHdlbjhyYm05In0.6bXLpBBZJCFXeYMX6pjL9w';
    map = new mapboxgl.Map({
        container: "map",
        style: 'mapbox://styles/mapbox/streets-v11', // stylesheet location
        center: [10, 15], // starting position [lng, lat]
        zoom: 0.95 // starting zoom
    });
}

function changeCenter() {
    let areaName = ["All", "Asia", "Europe", "America", "Africa", "Oceania"];
    let areaCenter = [
        [10, 15, 0.95],
        [120, 35, 1.7],
        [25, 50, 2.9],
        [-85, 20, 2],
        [20, 0, 2.3],
        [140, -25, 2.7]
    ];
    let area = document.getElementById("area");
    area = area.options[area.selectedIndex].value;
    area = areaName.indexOf(area);
    map.setCenter([areaCenter[area][0], areaCenter[area][1]]);
    map.setZoom(areaCenter[area][2]);
}