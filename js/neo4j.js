var app = angular.module('neo4j.module', []);

app.controller('Neo4jController', function($scope) {
    // Placeholder if we want to add more advanced behavior to the plugin
    $scope.config.neo4jUri = "bolt://localhost:7687";
});